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