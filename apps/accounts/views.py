from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.common.permissions import IsSelf

from .models import User
from .serializers import (
    LoginSerializer,
    RefreshSerializer,
    UserCreateSerializer,
    UserPublicSerializer,
    UserSelfSerializer,
)


class UserCreateView(generics.CreateAPIView):
    """POST /users — 회원가입 (Collection URI)."""

    queryset = User.objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        # 명세 0장: 생성 성공은 201 + Location 헤더 + 생성된 리소스 본문
        return Response(
            UserSelfSerializer(user).data,
            status=status.HTTP_201_CREATED,
            headers={"Location": f"{request.path.rstrip('/')}/{user.id}"},
        )


class UserDetailView(generics.RetrieveUpdateAPIView):
    """GET·PATCH /users/:userID — 본인=전체, 타인=공개 정보만 (판정은 토큰 기준)."""

    queryset = User.objects.select_related("character")
    http_method_names = ["get", "patch", "head", "options"]

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [IsAuthenticated(), IsSelf()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return UserSelfSerializer
        is_self = str(self.kwargs.get("pk")) == str(self.request.user.id)
        return UserSelfSerializer if is_self else UserPublicSerializer


class TokenView(APIView):
    """POST /tokens 로그인 / DELETE /tokens 로그아웃 (토큰 무효화)."""

    def get_permissions(self):
        return [IsAuthenticated()] if self.request.method == "DELETE" else [AllowAny()]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            # simplejwt 의 TokenError 는 DRF 예외가 아니라 그냥 두면 500 으로 샌다.
            raise InvalidToken("로그인에 실패했습니다. 다시 시도해 주세요.") from exc
        return Response(serializer.validated_data, status=status.HTTP_200_OK)

    def delete(self, request):
        raw = request.data.get("refresh_token")
        if not raw:
            raise ValidationError("refresh_token 은 필수 항목입니다.")
        try:
            RefreshToken(raw).blacklist()
        except TokenError:
            raise ValidationError("이미 만료되었거나 유효하지 않은 refresh_token 입니다.")
        return Response(status=status.HTTP_204_NO_CONTENT)


class TokenRefreshView(APIView):
    """POST /tokens/refresh — access_token 재발급 (Control Resource URI)."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RefreshSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            # 만료·위조·블랙리스트(로그아웃했거나 이미 회전된 토큰)를 한 문장으로 묶는다.
            # 어느 쪽인지 알려주지 않는 편이 보안상으로도 낫다.
            raise InvalidToken(
                "refresh_token 이 만료되었거나 유효하지 않습니다. 다시 로그인해 주세요."
            ) from exc
        return Response(serializer.validated_data, status=status.HTTP_200_OK)
