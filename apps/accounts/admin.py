from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["-created_at"]
    list_display = ["id", "email", "nickname", "is_admin", "created_at"]
    list_filter = ["is_admin", "is_active", "agree_marketing"]
    search_fields = ["email", "nickname", "phone"]
    readonly_fields = ["last_login", "created_at", "updated_at"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("개인정보", {"fields": ("nickname", "birth", "phone")}),
        ("약관 동의", {"fields": ("agree_data", "agree_marketing")}),
        ("알림 설정", {"fields": ("notify_memory", "notify_place", "notify_ad")}),
        (
            "권한",
            {"fields": ("is_active", "is_admin")},
        ),
        ("기록", {"fields": ("last_login", "created_at", "updated_at")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "nickname", "password1", "password2"),
            },
        ),
    )

    filter_horizontal = ()
