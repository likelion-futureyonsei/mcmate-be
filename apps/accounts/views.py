from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
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
    """GET /users/:userID — 유저 조회 (Element URI)
    PATCH /users/:userID — 알림 설정 토글 및 개인정보 부분 수정

    본인이면 전체, 타인이면 공개 정보만 내려준다.
    판정은 URL 의 :userID 가 아니라 **토큰에서 꺼낸 request.user.id** 로 한다.
    """

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
    """POST /tokens — 로그인 (Collection URI: 토큰 발급)
    DELETE /tokens — 로그아웃 (발급된 토큰 무효화)

    도한님 피드백대로 `/auth` 가 아니라 리소스 관점의 `/tokens` 를 쓴다.
    """

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

        if raw:
            # 이 기기 하나만 로그아웃
            try:
                RefreshToken(raw).blacklist()
            except TokenError:
                raise ValidationError("이미 만료되었거나 유효하지 않은 refresh_token 입니다.")
        else:
            # refresh_token 을 안 보냈으면 이 유저의 모든 기기를 로그아웃시킨다.
            for token in OutstandingToken.objects.filter(user=request.user):
                BlacklistedToken.objects.get_or_create(token=token)

        # 명세 0장: 삭제 성공은 204 No Content
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
