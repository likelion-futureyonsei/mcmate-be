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


class MemoryUpdateSerializer(serializers.ModelSerializer):
    """PATCH /memories/:memoryID 입력.

    수정 가능한 것은 사진·장소명·글·공개 설정뿐이다.
    좌표와 담긴 제품은 "그때 그 자리"의 기록이므로 바꿀 수 없다.
    """

    photo_key = serializers.CharField(
        source="photo", required=False, allow_blank=True, max_length=255
    )

    class Meta:
        model = Memory
        fields = ["photo_key", "place_name", "note", "visibility"]
