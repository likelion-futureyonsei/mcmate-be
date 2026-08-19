from rest_framework import generics, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.characters.models import Character
from apps.common.exceptions import DomainConflict

from .models import Product, UserProduct
from .serializers import ProductSerializer, UserProductCreateSerializer, UserProductSerializer


class ProductListCreateView(generics.ListCreateAPIView):
    def get_serializer_class(self):
        return UserProductCreateSerializer if self.request.method == "POST" else UserProductSerializer

    def get_queryset(self):
        # 시리얼이 포함되므로 본인 목록만 연다
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

        # 시리얼 충돌은 409 로 구분한다
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


class RecommendView(APIView):
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

        # 패턴 일치를 색상 일치보다 우선한다
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

        # 더 큰 용량 우선, 없으면 나머지에서 추천
        bigger = candidates.filter(capacity__gt=base.capacity)
        picks = (bigger or candidates).order_by("capacity")[: self.LIMIT]
        return Response(ProductSerializer(picks, many=True).data)
