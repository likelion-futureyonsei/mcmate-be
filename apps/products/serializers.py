from rest_framework import serializers

from .models import Product, UserProduct


class ProductSerializer(serializers.ModelSerializer):
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
