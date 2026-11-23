from django.core.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission


class IsOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        owner = getattr(obj, "owner", None)
        return bool(owner is None or owner == request.user or request.user.is_superuser)


class OwnerRequiredMixin:
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        owner = getattr(obj, "owner", None)
        if owner and owner != self.request.user and not self.request.user.is_superuser:
            raise PermissionDenied("You do not own this resource.")
        return obj
