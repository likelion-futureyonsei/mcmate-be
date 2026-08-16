from django.contrib import admin

from .models import Memory, Place


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    """특별 장소(포켓스탑) 시드 입력용.

    `GET /places` 는 v0.5 에서 보류됐지만, 해금 판정이 이 표를 읽는다.
    좌표와 radius 를 넣어두지 않으면 장소 스토리북이 영원히 안 열린다.
    """

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
