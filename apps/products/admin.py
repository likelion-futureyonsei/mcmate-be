from django.contrib import admin

from .models import Product, UserProduct


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """제품 마스터 시드 입력용. 팀원이 여기에 직접 채워 넣으면 된다."""

    list_display = ["id", "name", "product_code", "line", "color", "capacity", "storybook"]
    list_filter = ["line", "pattern", "color"]
    search_fields = ["name", "product_code"]
    list_editable = ["capacity"]
    autocomplete_fields = ["storybook"]
    fieldsets = (
        ("기본", {"fields": ("name", "product_code", "image_url")}),
        ("외형", {"fields": ("line", "pattern", "color")}),
        (
            "추억구슬",
            {
                "fields": ("capacity", "storybook"),
                "description": "capacity 는 이 제품에 담을 수 있는 추억구슬 개수다. "
                "제안값 — 지갑 10 / 크로스백 20 / 백팩 30.",
            },
        ),
        ("고객 정보", {"fields": ("warranty_months", "care_guide")}),
    )


@admin.register(UserProduct)
class UserProductAdmin(admin.ModelAdmin):
    list_display = ["id", "owner", "product", "serial_no", "acquired_at"]
    search_fields = ["serial_no", "owner__nickname", "owner__email", "product__name"]
    autocomplete_fields = ["owner", "product"]
    readonly_fields = ["acquired_at"]
