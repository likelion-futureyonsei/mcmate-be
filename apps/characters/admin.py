from django.contrib import admin

from .models import Character


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = ["id", "owner", "doll", "pattern", "color", "equipped_product"]
    list_filter = ["doll", "pattern", "color"]
    search_fields = ["owner__nickname", "owner__email"]
    autocomplete_fields = ["owner", "equipped_product"]
