from django.db import models

from apps.common.models import TimeStampedModel


class Storybook(TimeStampedModel):
    """명세 7장 storybooks 테이블. 시드 데이터.

    scope 로 두 종류를 구분한다.
      - product: 제품과 함께한 여정 (추억구슬 작성 수로 해금)
      - place  : 특별 장소 스토리 (해당 좌표 반경 안에서 작성 시 해금)
    """

    class Scope(models.TextChoices):
        PRODUCT = "product", "제품"
        PLACE = "place", "특별 장소"

    scope = models.CharField("종류", max_length=10, choices=Scope.choices)
    title = models.CharField("제목", max_length=120)
    cover_url = models.URLField("표지 이미지 URL", blank=True)

    class Meta:
        db_table = "storybooks"
        verbose_name = "스토리북"
        verbose_name_plural = "스토리북"

    def __str__(self):
        return f"[{self.get_scope_display()}] {self.title}"


class Chapter(TimeStampedModel):
    """명세 7장 chapters 테이블. 시드 데이터.

    required_memories: 이 챕터가 열리는 데 필요한 추억구슬 수.
    장소 스토리북의 첫 챕터처럼 방문만으로 열리는 경우는 0.
    """

    storybook = models.ForeignKey(
        Storybook, on_delete=models.CASCADE, related_name="chapters", verbose_name="스토리북"
    )
    chapter_no = models.PositiveIntegerField("챕터 번호")
    title = models.CharField("제목", max_length=120)
    body = models.TextField("본문", blank=True)
    required_memories = models.PositiveIntegerField(
        "해금 필요 추억 수", default=0, help_text="이 개수 이상 추억을 담으면 열린다."
    )

    class Meta:
        db_table = "chapters"
        verbose_name = "챕터"
        verbose_name_plural = "챕터"
        ordering = ["storybook_id", "chapter_no"]
        constraints = [
            models.UniqueConstraint(
                fields=["storybook", "chapter_no"], name="uniq_chapter_no_per_storybook"
            )
        ]

    def __str__(self):
        return f"{self.storybook.title} #{self.chapter_no} {self.title}"


class Unlock(models.Model):
    """명세 7장 unlocks 테이블. 어떤 유저가 어떤 챕터를 언제 열었는지."""

    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="unlocks", verbose_name="유저"
    )
    chapter = models.ForeignKey(
        Chapter, on_delete=models.CASCADE, related_name="unlocks", verbose_name="챕터"
    )
    unlocked_at = models.DateTimeField("해금 시각", auto_now_add=True)

    class Meta:
        db_table = "unlocks"
        verbose_name = "해금 이력"
        verbose_name_plural = "해금 이력"
        ordering = ["-unlocked_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "chapter"], name="uniq_unlock_per_user_chapter")
        ]

    def __str__(self):
        return f"{self.user.nickname} -> {self.chapter}"
