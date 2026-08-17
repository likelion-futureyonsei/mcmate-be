import uuid

from django.core.files.storage import default_storage
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.exceptions import DomainConflict
from apps.common.permissions import IsOwnerOrReadOnlyIfPublic

from .models import Memory
from .serializers import MemoryCreateSerializer, MemorySerializer, MemoryUpdateSerializer
from .services import distance_m, process_unlocks


class UploadView(APIView):
    """POST /upload — 추억 사진 업로드 (Control Resource).

    저장된 객체의 key 를 돌려주고, 프론트는 그 key 를 POST /memories 의
    photo_key 로 보낸다. 제품 등록에는 사용하지 않는다 (명세 1장).
    """

    parser_classes = [MultiPartParser, FormParser]
    MAX_SIZE = 10 * 1024 * 1024  # 10MB

    def post(self, request):
        file = request.FILES.get("file")
        if file is None:
            raise ValidationError("file 필드에 업로드할 파일을 담아 주세요.")
        if file.size > self.MAX_SIZE:
            raise ValidationError("파일은 10MB 이하여야 합니다.")

        ext = (file.name.rsplit(".", 1)[-1] if "." in file.name else "bin").lower()
        key = f"memories/{uuid.uuid4().hex}.{ext}"
        saved = default_storage.save(key, file)

        return Response(
            {"key": saved, "url": default_storage.url(saved)},
            status=status.HTTP_201_CREATED,
        )


class MemoryListCreateView(generics.ListCreateAPIView):
    """POST /memories — 추억 작성 (명세 4장, 서비스의 심장)
    GET  /memories — 추억 조회 (쿼리 파라미터 필터링)

    [작성 서버 로직]
    ① 용량 체크 (가득 차면 409)
    ② 특별 장소 좌표 매칭 해금  ③ 작성 수 기준 챕터 해금   -> services.process_unlocks
    ④ 해금 정보를 unlocked 로 포함해 201 Created

    [조회 필터] ?lat=&lng=&radius= (지도 주변) / ?product_id= / ?owner={userID}
    타 유저의 추억은 공개(public) 설정된 것만 보인다.
    """

    def get_serializer_class(self):
        return MemoryCreateSerializer if self.request.method == "POST" else MemorySerializer

    def get_queryset(self):
        # 기본 노출 범위: 모두의 공개 추억 + 나의 비공개 추억
        qs = (
            Memory.objects.select_related("user_product")
            .filter(Q(visibility=Memory.Visibility.PUBLIC) | Q(owner=self.request.user))
        )

        params = self.request.query_params
        if owner := params.get("owner"):
            qs = qs.filter(owner_id=owner)
        if product_id := params.get("product_id"):
            qs = qs.filter(user_product_id=product_id)

        lat, lng, radius = params.get("lat"), params.get("lng"), params.get("radius")
        if lat and lng and radius:
            try:
                lat, lng, radius = float(lat), float(lng), float(radius)
            except ValueError:
                raise ValidationError("lat, lng, radius 는 숫자여야 합니다.")
            # 시연 규모(수백 건)에서는 정밀 거리 계산을 파이썬에서 해도 충분하다.
            return [m for m in qs if distance_m(m.lat, m.lng, lat, lng) <= radius]
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_product = serializer.validated_data["user_product"]

        # ① 용량 체크 — 명세 8장의 409 응답 그대로
        if user_product.is_full:
            raise DomainConflict("이 제품의 추억이 가득 찼습니다.")

        memory = serializer.save(owner=request.user)

        # ②③ 해금 판정
        unlocked = process_unlocks(memory)

        # ④ 응답 — 명세 8장 예시 형태
        payload = {
            "id": memory.id,
            "created_at": memory.created_at.isoformat(),
            "capacity": {"used": user_product.capacity_used, "total": user_product.capacity_total},
            "unlocked": unlocked,
        }
        return Response(
            payload,
            status=status.HTTP_201_CREATED,
            headers={"Location": f"/api/v1/memories/{memory.id}"},
        )


class MemoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET    /memories/:memoryID — 상세 (작성자 식별용 owner 포함, 명세 4장)
    PATCH  /memories/:memoryID — 부분 수정 (본인 것만)
    DELETE /memories/:memoryID — 삭제, 204 No Content (본인 것만)

    조회는 본인 전부 + 타인 공개만. 수정·삭제는 본인만 (권한은 토큰 기준 판정).
    """

    queryset = Memory.objects.select_related("user_product")
    permission_classes = [IsOwnerOrReadOnlyIfPublic]
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_serializer_class(self):
        return MemoryUpdateSerializer if self.request.method == "PATCH" else MemorySerializer

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True  # PUT 없이 항상 부분 수정
        super().update(request, *args, **kwargs)
        # 수정 응답도 조회와 같은 전체 형태로 돌려준다
        return Response(MemorySerializer(self.get_object()).data)
