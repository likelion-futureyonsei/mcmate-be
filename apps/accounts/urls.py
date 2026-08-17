from django.urls import path

from .views import TokenRefreshView, TokenView, UserCreateView, UserDetailView

# 명세 0장: URI 는 명사·소문자·복수형, 끝에 `/` 없음.
urlpatterns = [
    # 1장 인프라 & 제어
    path("tokens", TokenView.as_view(), name="token"),  # POST 로그인 / DELETE 로그아웃
    path("tokens/refresh", TokenRefreshView.as_view(), name="token-refresh"),
    # 2장 사용자
    path("users", UserCreateView.as_view(), name="user-create"),
    path("users/<int:pk>", UserDetailView.as_view(), name="user-detail"),
]
