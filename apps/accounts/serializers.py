from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer

from apps.characters.models import Character

from .models import User


class CharacterBriefSerializer(serializers.ModelSerializer):
    """유저 조회에 싣는 캐릭터 요약 — 모델만 참조, 캐릭터 API 는 apps/characters."""

    class Meta:
        model = Character
        fields = ["id", "doll_type", "pattern", "color", "equipped_product"]


class UserCreateSerializer(serializers.ModelSerializer):
    """POST /users — 회원가입."""

    password = serializers.CharField(
        write_only=True, validators=[validate_password], style={"input_type": "password"}
    )
    email = serializers.EmailField(
        error_messages={"invalid": "이메일 형식이 올바르지 않습니다."}
    )

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "password",
            "nickname",
            "birth",
            "phone",
            "agree_data",
            "agree_marketing",
        ]

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("이미 가입된 이메일입니다.")
        return value.lower()

    def validate_agree_data(self, value):
        if not value:
            raise serializers.ValidationError("개인정보 수집·이용에 동의해야 가입할 수 있습니다.")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)


class UserSelfSerializer(serializers.ModelSerializer):
    """본인 조회 — 자동 로그인 유지 및 설정 화면용."""

    character = CharacterBriefSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "nickname",
            "birth",
            "phone",
            "agree_data",
            "agree_marketing",
            "notify_memory",
            "notify_place",
            "notify_ad",
            "character",
            "created_at",
        ]
        # agree_data 철회는 탈퇴로만 — PATCH 로 끌 수 없다 (배경은 PR #2 참고)
        read_only_fields = ["id", "email", "agree_data", "created_at"]


class UserPublicSerializer(serializers.ModelSerializer):
    """타인 조회 — 장착 제품/캐릭터 뷰어용. 연락처·약관·알림 설정은 내려주지 않는다."""

    character = CharacterBriefSerializer(read_only=True)

    class Meta:
        model = User
        fields = ["id", "nickname", "character"]


class LoginSerializer(TokenObtainPairSerializer):
    """POST /tokens — 로그인. 토큰 2종 + user_id 반환 (명세 1장)."""

    username_field = User.USERNAME_FIELD

    default_error_messages = {
        "no_active_account": "이메일 또는 비밀번호가 올바르지 않습니다.",
    }

    def validate(self, attrs):
        data = super().validate(attrs)
        return {
            "user_id": self.user.id,
            "nickname": self.user.nickname,
            "access_token": data["access"],
            "refresh_token": data["refresh"],
        }


class RefreshSerializer(TokenRefreshSerializer):
    """POST /tokens/refresh — 재발급. 필드명만 명세(refresh_token)에 맞춘다."""

    refresh = None  # 부모의 내부 필드명이 에러 메시지로 새지 않게 제거

    refresh_token = serializers.CharField(
        write_only=True,
        error_messages={
            "required": "refresh_token 은 필수 항목입니다.",
            "blank": "refresh_token 을 입력해 주세요.",
        },
    )

    def validate(self, attrs):
        data = super().validate({"refresh": attrs["refresh_token"]})
        result = {"access_token": data["access"]}
        if "refresh" in data:  # ROTATE_REFRESH_TOKENS=True 이면 새 refresh 도 함께 발급된다
            result["refresh_token"] = data["refresh"]
        return result
