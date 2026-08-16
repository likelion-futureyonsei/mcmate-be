from django.db import models

from apps.common.models import TimeStampedModel


class Character(TimeStampedModel):
    """명세 7장 characters 테이블. 유저당 1개(1:1).

    관련 API (POST /characters, PATCH /characters/:characterID,
    GET /characters?owner={userID}) 는 이 앱 안에서 구현한다.
    """

    class Doll(models.TextChoices):
        BEARBRICK = "bearbrick", "베어브릭"
        RABBIT = "rabbit", "토끼"
        PUPPY = "puppy", "퍼피"
        DACHSHUND = "dachshund", "닥스훈트"

    class Pattern(models.TextChoices):
        VISETOS = "visetos", "비세토스"
        LAURETOS = "lauretos", "로레토스"
        CUBIC_MONOGRAM = "cubic_monogram", "큐빅 모노그램"

    class Color(models.TextChoices):
        COGNAC = "cognac", "꼬냑"
        BLACK = "black", "블랙"
        WHITE = "white", "화이트"
        SILVER = "silver", "실버"
        PINK = "pink", "핑크"

    owner = models.OneToOneField(
        "accounts.User", on_delete=models.CASCADE, related_name="character", verbose_name="소유자"
    )
    doll_type = models.CharField("인형", max_length=20, choices=Doll.choices)
    pattern = models.CharField("패턴", max_length=20, choices=Pattern.choices)
    color = models.CharField("색상", max_length=20, choices=Color.choices)
    equipped_product = models.ForeignKey(
        "products.UserProduct",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="equipped_by",
        verbose_name="장착 제품",
        help_text="홈 화면 상단 용량 게이지는 이 제품 하나의 값을 쓴다.",
    )

    class Meta:
        db_table = "characters"
        verbose_name = "캐릭터"
        verbose_name_plural = "캐릭터"

    def __str__(self):
        return f"{self.owner.nickname}의 {self.get_doll_type_display()}"
