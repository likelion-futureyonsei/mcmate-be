from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsOwner(BasePermission):
    """소유자 본인만 허용. 판정은 ?owner= 가 아니라 토큰의 유저 ID (보안 원칙)."""

    owner_field = "owner_id"
    message = "본인의 리소스만 접근할 수 있습니다."

    def has_object_permission(self, request, view, obj):
        field = getattr(view, "owner_field", self.owner_field)
        return getattr(obj, field, None) == request.user.id


class IsOwnerOrReadOnlyIfPublic(IsOwner):
    """본인은 전부 가능, 타인은 공개(public)로 설정된 것만 읽기 가능."""

    message = "비공개 추억이거나 본인의 리소스가 아닙니다."

    def has_object_permission(self, request, view, obj):
        if super().has_object_permission(request, view, obj):
            return True
        return request.method in SAFE_METHODS and getattr(obj, "visibility", None) == "public"


class IsSelf(BasePermission):
    """`/users/:userID` 처럼 대상 객체가 곧 유저인 경우."""

    message = "본인 계정만 수정할 수 있습니다."

    def has_object_permission(self, request, view, obj):
        return obj.pk == request.user.id
