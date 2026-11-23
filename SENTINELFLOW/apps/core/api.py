from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.models import ROLE_ANALYST, ROLE_ADMIN


def _is_security_staff(user):
    return bool(user and user.is_authenticated and (user.is_superuser or getattr(user, "role", None) in {ROLE_ADMIN, ROLE_ANALYST}))


class IsSecurityStaff(BasePermission):
    message = "This action requires an administrator or security analyst role."

    def has_permission(self, request, view):
        return _is_security_staff(request.user)


class IsReadOnlyForViewer(BasePermission):
    message = "Viewers may only read data. State changes require analyst privileges."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.method in SAFE_METHODS or _is_security_staff(request.user)


def restrict_to_self(viewset, queryset, user_field="user"):
    user = viewset.request.user
    if user.is_authenticated and not _is_security_staff(user):
        return queryset.filter(**{user_field: user})
    return queryset
