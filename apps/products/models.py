from django.db import models

from apps.common.models import TimeStampedModel


class Product(TimeStampedModel):
    name = models.CharField("제품명", max_length=100)
    line = models.CharField("라인", max_length=50, blank=True)
    pattern = models.CharField("패턴", max_length=50, blank=True)
    color = models.CharField("색상", max_length=50, blank=True)
    product_code = models.CharField("제품 코드", max_length=50, unique=True)
    capacity = models.PositiveIntegerField(
        "추억구슬 용량", default=20, help_text="이 제품에 담을 수 있는 추억구슬 개수"
    )
    warranty_months = models.PositiveIntegerField("보증 기간(개월)", default=24)
    care_guide = models.TextField("보관법", blank=True)
    image_url = models.URLField("이미지 URL", blank=True)
    storybook = models.ForeignKey(
        "storybooks.Storybook",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        verbose_name="연관 스토리북",
    )

    class Meta:
        db_table = "products"
        verbose_name = "제품(마스터)"
        verbose_name_plural = "제품(마스터)"

    def __str__(self):
        return f"{self.name} ({self.product_code})"


class UserProduct(TimeStampedModel):
    owner = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="products", verbose_name="소유자"
    )
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="owned_by", verbose_name="제품"
    )
    serial_no = models.CharField("시리얼 번호", max_length=64, unique=True)
    acquired_at = models.DateTimeField("등록 시각", auto_now_add=True)

    class Meta:
        db_table = "user_products"
        verbose_name = "보유 제품"
        verbose_name_plural = "보유 제품"
        ordering = ["-acquired_at"]

    def __str__(self):
        return f"{self.owner.nickname} / {self.product.name} / {self.serial_no}"

    @property
    def capacity_total(self) -> int:
        return self.product.capacity

    @property
    def capacity_used(self) -> int:
        return self.memories.count()

    @property
    def is_full(self) -> bool:
        return self.capacity_used >= self.capacity_total
