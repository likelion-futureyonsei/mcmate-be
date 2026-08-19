from rest_framework import serializers

from .models import Character


class CharacterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Character
        fields = [
            "id", "owner", "doll", "pattern", "color",
            "equipped_product", "created_at",
        ]
        read_only_fields = ["id", "owner", "created_at"]

    def validate_equipped_product(self, value):
        if value is not None and value.owner_id != self.context["request"].user.id:
            raise serializers.ValidationError("본인 보유 제품만 장착할 수 있습니다.")
        return value
    