from rest_framework import serializers

from .models import Product, UserProduct


class ProductSerializer(serializers.ModelSerializer):
    """제품 마스터. GET /recommend 응답에도 그대로 쓰인다."""

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "line",
            "pattern",
            "color",
            "product_code",
            "capacity",
            "warranty_months",
            "care_guide",
            "image_url",
            "storybook",
        ]


class UserProductSerializer(serializers.ModelSerializer):
    """보유 제품 — 목록·등록 응답.

    명세 3장: 남은 용량 게이지와 추억 수를 함께 내려준다.
    """

    product = ProductSerializer(read_only=True)
    capacity = serializers.SerializerMethodField()
    memory_count = serializers.SerializerMethodField()

    class Meta:
        model = UserProduct
        fields = ["id", "owner", "product", "serial_no", "acquired_at", "capacity", "memory_count"]
        read_only_fields = ["id", "owner", "acquired_at"]

    def get_capacity(self, obj) -> dict:
        # len(all()) 은 prefetch 캐시를 타므로 목록에서 행마다 쿼리가 나가지 않는다
        return {"used": len(obj.memories.all()), "total": obj.product.capacity}

    def get_memory_count(self, obj) -> int:
        return len(obj.memories.all())


class UserProductCreateSerializer(serializers.ModelSerializer):
    """POST /products 입력.

    serial_no 를 모델 필드 그대로 두면 unique 검증이 400 을 돌려주는데,
    명세는 시리얼 충돌을 409(도메인 충돌)로 구분하므로
    여기서는 형식 검사만 하고 중복 판정은 뷰에서 한다.
    """

    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source="product",
        error_messages={
            "does_not_exist": "존재하지 않는 제품입니다.",
            "incorrect_type": "product_id 는 숫자여야 합니다.",
        },
    )
    serial_no = serializers.CharField(
        max_length=64,
        error_messages={
            "required": "serial_no 는 필수 항목입니다.",
            "blank": "serial_no 를 입력해 주세요.",
        },
    )

    class Meta:
        model = UserProduct
        fields = ["product_id", "serial_no"]
