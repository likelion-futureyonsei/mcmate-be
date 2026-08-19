from django.urls import path

from .views import ProductListCreateView, RecommendView

urlpatterns = [
    # 3장 제품
    path("products", ProductListCreateView.as_view(), name="product-list"),
    # 1장 인프라 & 제어 — 제품 추천 (Control Resource)
    path("recommend", RecommendView.as_view(), name="recommend"),
]
