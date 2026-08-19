from django.urls import path

from .views import StorybookDetailView, StorybookListView

urlpatterns = [
    # 5장 스토리북
    path("storybooks", StorybookListView.as_view(), name="storybook-list"),
    path("storybooks/<int:pk>", StorybookDetailView.as_view(), name="storybook-detail"),
]
