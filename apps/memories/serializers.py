from rest_framework import serializers

from apps.products.models import UserProduct

from .models import Memory


class MemorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Memory
        fields = [
            "id",
            "owner",
            "user_product",
            "photo",
            "lat",
            "lng",
            "place_name",
            "note",
            "visibility",
            "created_at",
        ]
        read_only_fields = ["id", "owner", "created_at"]


class MemoryCreateSerializer(serializers.ModelSerializer):
    user_product_id = serializers.PrimaryKeyRelatedField(
        queryset=UserProduct.objects.all(),
        source="user_product",
        error_messages={
            "does_not_exist": "보유 제품을 찾을 수 없습니다.",
            "incorrect_type": "user_product_id 는 숫자여야 합니다.",
        },
    )
    photo_key = serializers.CharField(
        source="photo", required=False, allow_blank=True, max_length=255
    )

    class Meta:
        model = Memory
        fields = ["user_product_id", "photo_key", "lat", "lng", "place_name", "note", "visibility"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 본인 보유 제품만 선택할 수 있다
        request = self.context.get("request")
        if request is not None:
            self.fields["user_product_id"].queryset = UserProduct.objects.filter(
                owner=request.user
            )
