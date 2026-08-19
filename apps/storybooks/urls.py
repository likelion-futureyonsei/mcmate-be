from django.urls import path

from .views import GenerateView, StorybookDetailView, StorybookListView

urlpatterns = [
    path("generate", GenerateView.as_view(), name="generate"),
    # 5장 스토리북
    path("storybooks", StorybookListView.as_view(), name="storybook-list"),
    path("storybooks/<int:pk>", StorybookDetailView.as_view(), name="storybook-detail"),
]
