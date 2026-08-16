from django.urls import path

from .views import MemoryCreateView, UploadView

urlpatterns = [
    # 1장 인프라 & 제어 — 파일 업로드 (Control Resource)
    path("upload", UploadView.as_view(), name="upload"),
    # 4장 추억구슬
    path("memories", MemoryCreateView.as_view(), name="memory-list"),
]
