import logging
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

from apps.storybooks.models import GeneratedStory
from apps.storybooks.services import generate_story

from .models import Memory
from .serializers import MemoryCreateSerializer, MemorySerializer, MemoryUpdateSerializer
from .services import distance_m, matched_place_storybooks, process_unlocks


class UploadView(APIView):
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

        # 용량 체크
        if user_product.is_full:
            raise DomainConflict("이 제품의 추억이 가득 찼습니다.")

        memory = serializer.save(owner=request.user)

        # 해금 판정
        unlocked = process_unlocks(memory)

        # 장소 매칭 시 AI 스토리 자동 생성 (기획 결정). 실패해도 추억 저장은 성공한다
        for storybook in matched_place_storybooks(memory):
            if GeneratedStory.objects.filter(user=request.user, storybook=storybook).exists():
                continue
            try:
                generate_story(request.user, storybook)
            except Exception as exc:
                logging.getLogger(__name__).warning(
                    "AI 스토리 자동 생성 실패 (storybook=%s): %s", storybook.id, exc
                )

        # 응답 구성
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
