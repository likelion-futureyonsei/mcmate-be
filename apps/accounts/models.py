from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models

from apps.common.models import TimeStampedModel


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra):
        if not email:
            raise ValueError("이메일은 필수입니다.")
        user = self.model(email=self.normalize_email(email), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        return self._create_user(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra["is_admin"] = True
        extra.setdefault("nickname", "admin")
        return self._create_user(email, password, **extra)


class User(AbstractBaseUser, TimeStampedModel):
    email = models.EmailField("이메일", unique=True)
    nickname = models.CharField("닉네임", max_length=30)
    birth = models.DateField("생년월일", null=True, blank=True)
    phone = models.CharField("전화번호", max_length=20, blank=True)

    agree_data = models.BooleanField("개인정보 수집·이용 동의", default=False)
    agree_marketing = models.BooleanField("마케팅 수신 동의", default=False)

    notify_memory = models.BooleanField("근처 추억구슬 알림", default=True)
    notify_place = models.BooleanField("특별 장소 알림", default=True)
    notify_ad = models.BooleanField("광고성 알림", default=False)

    is_active = models.BooleanField("활성", default=True)
    is_admin = models.BooleanField("최고 관리자", default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nickname"]

    class Meta:
        db_table = "users"
        verbose_name = "유저"
        verbose_name_plural = "유저"

    def __str__(self):
        return f"{self.nickname} <{self.email}>"

    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, app_label):
        return self.is_admin

    @property
    def is_staff(self):
        return self.is_admin

    @property
    def is_superuser(self):
        return self.is_admin
