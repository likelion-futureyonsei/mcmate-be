from django.contrib import admin

from .models import Chapter, Storybook, Unlock


class ChapterInline(admin.TabularInline):
    model = Chapter
    extra = 1
    fields = ["chapter_no", "title", "required_memories", "body"]
    ordering = ["chapter_no"]


@admin.register(Storybook)
class StorybookAdmin(admin.ModelAdmin):
    list_display = ["id", "scope", "title", "chapter_count"]
    list_filter = ["scope"]
    search_fields = ["title"]
    inlines = [ChapterInline]

    @admin.display(description="챕터 수")
    def chapter_count(self, obj):
        return obj.chapters.count()


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ["id", "storybook", "chapter_no", "title", "required_memories"]
    list_filter = ["storybook__scope", "storybook"]
    search_fields = ["title", "body"]
    autocomplete_fields = ["storybook"]


@admin.register(Unlock)
class UnlockAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "chapter", "unlocked_at"]
    search_fields = ["user__nickname", "user__email", "chapter__title"]
    autocomplete_fields = ["user", "chapter"]
    readonly_fields = ["unlocked_at"]
