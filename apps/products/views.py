from rest_framework import generics, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.characters.models import Character
from apps.common.exceptions import DomainConflict
from apps.common.permissions import IsOwner

from .models import Product, UserProduct
from .serializers import ProductSerializer, UserProductCreateSerializer, UserProductSerializer


class ProductListCreateView(generics.ListCreateAPIView):
    """POST /products — 제품 등록 (Collection URI)
    GET  /products?owner={userID} — 보유 제품 목록

    시리얼 인식은 프론트가 OCR 처리 후 텍스트만 보낸다. 사진 첨부 없음 (명세 3장).
    """

    def get_serializer_class(self):
        return UserProductCreateSerializer if self.request.method == "POST" else UserProductSerializer

    def get_queryset(self):
        # 명세 3장: 보유 제품 목록은 "특정 유저(본인)" 용도다. 시리얼 번호가 포함되므로
        # 타인 목록은 열어주지 않는다. 판정은 쿼리가 아니라 토큰의 유저 ID 로 한다.
        owner = self.request.query_params.get("owner") or self.request.user.id
        if str(owner) != str(self.request.user.id):
            raise PermissionDenied("보유 제품 목록은 본인만 조회할 수 있습니다.")
        return (
            UserProduct.objects.filter(owner_id=self.request.user.id)
            .select_related("product")
            .prefetch_related("memories")
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 시리얼 충돌은 형식 오류(400)가 아니라 도메인 충돌(409) — 사유를 구분해 명시한다.
        existing = UserProduct.objects.filter(
            serial_no=serializer.validated_data["serial_no"]
        ).first()
        if existing is not None:
            if existing.owner_id == request.user.id:
                raise DomainConflict("이미 등록한 시리얼 번호입니다.")
            raise DomainConflict("다른 사용자가 소유한 시리얼 번호입니다.")

        user_product = serializer.save(owner=request.user)
        return Response(
            UserProductSerializer(user_product).data,
            status=status.HTTP_201_CREATED,
            headers={"Location": f"/api/v1/products/{user_product.id}"},
        )


class UserProductDetailView(generics.RetrieveAPIView):
    """GET /products/:productID — 제품 상세 (Element URI).

    보증 기간·보관법·남은 용량·연관 스토리북 ID (명세 3장).
    홈 화면 상단 용량 표시는 캐릭터가 장착 중인 제품 하나의 값 — 프론트는
    characters 의 equipped_product 로 이 주소를 호출한다.
    시리얼이 포함되므로 본인 것만 조회 가능.
    """

    queryset = UserProduct.objects.select_related("product__storybook")
    serializer_class = UserProductSerializer
    permission_classes = [IsOwner]


class RecommendView(APIView):
    """GET /recommend — 제품 추천 (Control Resource)

    ?character_id= : 캐릭터 외형(패턴·색) 기반 MCM 제품 추천
    ?product_id=   : 특정 제품 용량 소진 시 다음 여정(제품) 추천
                     (POST /memories 의 409 응답 links 가 이 주소를 가리킨다)
    """

    LIMIT = 3

    def get(self, request):
        if character_id := request.query_params.get("character_id"):
            return self._by_character(character_id)
        if product_id := request.query_params.get("product_id"):
            return self._by_product(request, product_id)
        raise ValidationError("character_id 또는 product_id 쿼리 파라미터가 필요합니다.")

    def _by_character(self, character_id):
        try:
            character = Character.objects.get(pk=character_id)
        except (Character.DoesNotExist, ValueError):
            raise NotFound("캐릭터를 찾을 수 없습니다.")

        # 패턴 일치를 색상 일치보다 우선한다 (외형 정체성이 패턴에 더 크게 걸림).
        def score(product: Product) -> int:
            s = 0
            if product.pattern == character.pattern:
                s += 2
            if product.color == character.color:
                s += 1
            return s

        products = sorted(Product.objects.all(), key=lambda p: (-score(p), p.capacity))
        return Response(ProductSerializer(products[: self.LIMIT], many=True).data)

    def _by_product(self, request, product_id):
        try:
            current = UserProduct.objects.select_related("product").get(
                pk=product_id, owner=request.user
            )
        except (UserProduct.DoesNotExist, ValueError):
            raise NotFound("보유 제품을 찾을 수 없습니다.")

        base = current.product
        candidates = Product.objects.exclude(pk=base.pk)

        # 다음 여정: 같은 라인의 상위 용량 > 더 큰 용량 > 그 외. 추천이 비는 일은 없게 한다.
        same_line_up = [p for p in candidates if p.line == base.line and p.capacity >= base.capacity]
        bigger = [p for p in candidates if p.capacity > base.capacity]
        picks = same_line_up or bigger or list(candidates)
        picks = sorted(picks, key=lambda p: p.capacity)[: self.LIMIT]
        return Response(ProductSerializer(picks, many=True).data)
