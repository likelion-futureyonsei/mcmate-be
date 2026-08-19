from django.urls import path

from .views import CharacterDetailView, CharacterListCreateView

urlpatterns = [
    path("characters", CharacterListCreateView.as_view(), name="character-list"),
    path("characters/<int:pk>", CharacterDetailView.as_view(), name="character-detail"),
]
