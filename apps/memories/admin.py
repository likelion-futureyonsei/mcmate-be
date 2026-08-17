from django.contrib import admin

from .models import Memory, Place


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    """특별 장소 시드 입력용 — 좌표·radius 가 없으면 장소 스토리북이 열리지 않는다."""

    list_display = ["id", "type", "name", "lat", "lng", "radius", "storybook"]
    list_filter = ["type"]
    search_fields = ["name", "address"]
    list_editable = ["radius"]
    autocomplete_fields = ["storybook"]


@admin.register(Memory)
class MemoryAdmin(admin.ModelAdmin):
    list_display = ["id", "owner", "user_product", "place_name", "visibility", "created_at"]
    list_filter = ["visibility", "created_at"]
    search_fields = ["place_name", "note", "owner__nickname"]
    autocomplete_fields = ["owner", "user_product"]
    readonly_fields = ["created_at", "updated_at"]
