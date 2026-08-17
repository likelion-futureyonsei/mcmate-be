from rest_framework import generics, status
from rest_framework.response import Response

from apps.common.exceptions import DomainConflict
from apps.common.permissions import IsOwner

from .models import Character
from .serializers import CharacterSerializer


class CharacterListCreateView(generics.ListCreateAPIView):
    serializer_class = CharacterSerializer

    def get_queryset(self):
        qs = Character.objects.select_related("owner", "equipped_product")
        if owner := self.request.query_params.get("owner"):
            qs = qs.filter(owner_id=owner)
        return qs

    def create(self, request, *args, **kwargs):
        if Character.objects.filter(owner=request.user).exists():
            raise DomainConflict("이미 캐릭터가 있습니다. 수정(PATCH)을 이용해 주세요.")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        character = serializer.save(owner=request.user)

        return Response(
            self.get_serializer(character).data,
            status=status.HTTP_201_CREATED,
            headers={"Location": f"/api/v1/characters/{character.id}"},
        )


class CharacterDetailView(generics.RetrieveUpdateAPIView):
    queryset = Character.objects.all()
    serializer_class = CharacterSerializer
    permission_classes = [IsOwner]
    http_method_names = ["get", "patch", "head", "options"]