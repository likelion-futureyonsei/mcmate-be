from rest_framework import serializers

from apps.products.models import UserProduct

from .models import Memory


class MemorySerializer(serializers.ModelSerializer):
    """추억구슬 조회 응답. owner 는 "작성자 캐릭터 보기" 연결용 (명세 4장)."""

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
    """POST /memories 입력 (명세 8장 요청 예시와 필드명을 맞춘다)."""

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
        # 본인 보유 제품에만 담을 수 있다 — 남의 제품 id 는 "없는 것"과 같게 취급한다
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
