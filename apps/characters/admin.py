from django.contrib import admin

from .models import Character


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = ["id", "owner", "doll_type", "pattern", "color", "equipped_product"]
    list_filter = ["doll_type", "pattern", "color"]
    search_fields = ["owner__nickname", "owner__email"]
    autocomplete_fields = ["owner", "equipped_product"]
