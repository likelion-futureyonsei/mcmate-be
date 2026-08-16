from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

from apps.common.models import TimeStampedModel


class UserManager(BaseUserManager):
    """이메일을 아이디로 쓰는 유저 매니저."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra):
        if not email:
            raise ValueError("이메일은 필수입니다.")
        user = self.model(email=self.normalize_email(email), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("nickname", "admin")
        if extra.get("is_staff") is not True or extra.get("is_superuser") is not True:
            raise ValueError("슈퍼유저는 is_staff, is_superuser 가 모두 True 여야 합니다.")
        return self._create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    """명세 7장 users 테이블.

    Django 기본 User 는 username 으로 로그인하지만 명세는 이메일 로그인이고,
    nickname/birth/phone/약관 동의/알림 설정을 담을 자리도 없다.
    비밀번호는 password 컬럼에 해시로만 저장된다(AbstractBaseUser 제공).
    토큰 테이블은 두지 않는다 — simplejwt 가 처리한다.
    """

    email = models.EmailField("이메일", unique=True)
    nickname = models.CharField("닉네임", max_length=30)
    birth = models.DateField("생년월일", null=True, blank=True)
    phone = models.CharField("전화번호", max_length=20, blank=True)

    # 약관 동의 2종
    agree_data = models.BooleanField("개인정보 수집·이용 동의", default=False)
    agree_marketing = models.BooleanField("마케팅 수신 동의", default=False)

    # 알림 설정 (PATCH /users/:userID 로 토글)
    notify_memory = models.BooleanField("근처 추억구슬 알림", default=True)
    notify_place = models.BooleanField("특별 장소 알림", default=True)
    notify_ad = models.BooleanField("광고성 알림", default=False)

    is_active = models.BooleanField("활성", default=True)
    is_staff = models.BooleanField("관리자 페이지 접근", default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nickname"]

    class Meta:
        db_table = "users"
        verbose_name = "유저"
        verbose_name_plural = "유저"

    def __str__(self):
        return f"{self.nickname} <{self.email}>"
