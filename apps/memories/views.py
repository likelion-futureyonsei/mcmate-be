import uuid

from django.core.files.storage import default_storage
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.exceptions import DomainConflict

from .serializers import MemoryCreateSerializer, MemorySerializer
from .services import process_unlocks


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


class MemoryCreateView(generics.CreateAPIView):
    """POST /memories — 추억 작성 (명세 4장, 서비스의 심장).

    ① 용량 체크 (가득 차면 409)
    ② 특별 장소 좌표 매칭 해금  ③ 작성 수 기준 챕터 해금   -> services.process_unlocks
    ④ 해금 정보를 unlocked 로 포함해 201 Created
    """

    serializer_class = MemoryCreateSerializer

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
