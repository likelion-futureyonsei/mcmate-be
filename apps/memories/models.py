from django.db import models

from apps.common.models import TimeStampedModel


class Place(TimeStampedModel):
    class Type(models.TextChoices):
        CITY = "city", "도시"
        STORE = "store", "매장"

    type = models.CharField("종류", max_length=10, choices=Type.choices)
    name = models.CharField("이름", max_length=100)
    address = models.CharField("주소", max_length=255, blank=True)
    lat = models.DecimalField("위도", max_digits=9, decimal_places=6)
    lng = models.DecimalField("경도", max_digits=9, decimal_places=6)
    radius = models.PositiveIntegerField("인식 반경(m)", default=200)
    storybook = models.ForeignKey(
        "storybooks.Storybook",
        on_delete=models.CASCADE,
        related_name="places",
        verbose_name="해금될 스토리북",
    )

    class Meta:
        db_table = "places"
        verbose_name = "특별 장소"
        verbose_name_plural = "특별 장소"

    def __str__(self):
        return f"[{self.get_type_display()}] {self.name}"


class Memory(TimeStampedModel):
    class Visibility(models.TextChoices):
        PUBLIC = "public", "공개"
        PRIVATE = "private", "비공개"

    owner = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="memories", verbose_name="작성자"
    )
    user_product = models.ForeignKey(
        "products.UserProduct",
        on_delete=models.CASCADE,
        related_name="memories",
        verbose_name="담은 제품",
    )
    photo = models.CharField(
        "사진 키", max_length=255, blank=True, help_text="POST /upload 가 돌려준 key"
    )
    lat = models.DecimalField("위도", max_digits=9, decimal_places=6)
    lng = models.DecimalField("경도", max_digits=9, decimal_places=6)
    place_name = models.CharField("장소명", max_length=100, blank=True)
    note = models.TextField("한 줄 기록", blank=True)
    visibility = models.CharField(
        "공개 설정", max_length=10, choices=Visibility.choices, default=Visibility.PUBLIC
    )

    class Meta:
        db_table = "memories"
        verbose_name = "추억구슬"
        verbose_name_plural = "추억구슬"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["lat", "lng"], name="idx_memory_latlng"),
            models.Index(fields=["owner", "-created_at"], name="idx_memory_owner_created"),
        ]

    def __str__(self):
        return f"{self.owner.nickname} @ {self.place_name or f'{self.lat},{self.lng}'}"
