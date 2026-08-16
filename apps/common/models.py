from django.db import models


class TimeStampedModel(models.Model):
    """생성·수정 시각을 공통으로 갖는 추상 모델."""

    created_at = models.DateTimeField("생성 시각", auto_now_add=True)
    updated_at = models.DateTimeField("수정 시각", auto_now=True)

    class Meta:
        abstract = True
