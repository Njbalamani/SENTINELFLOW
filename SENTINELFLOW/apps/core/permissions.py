from django.core.exceptions import PermissionDenied
from django.http import JsonResponse

from apps.accounts.models import ROLE_ADMIN, ROLE_ANALYST, ROLE_VIEWER

SAFE_METHODS = ("GET", "HEAD", "OPTIONS")


def has_role(user, *roles):
    return bool(user and user.is_authenticated and getattr(user, "role", None) in roles)


def is_admin(user):
    return has_role(user, ROLE_ADMIN) or bool(getattr(user, "is_superuser", False))


def is_analyst(user):
    return has_role(user, ROLE_ADMIN, ROLE_ANALYST) or bool(getattr(user, "is_superuser", False))


def require_roles(*roles):
    def decorator(view):
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied("Authentication is required.")
            if not has_role(request.user, *roles) and not request.user.is_superuser:
                raise PermissionDenied("You do not have permission to access this resource.")
            return view(request, *args, **kwargs)

        wrapped.__name__ = view.__name__
        wrapped.__doc__ = view.__doc__
        return wrapped

    return decorator


class RolePermissionMixin:
    """Read access for all staff roles; state changes require analyst privileges."""

    allowed_roles = (ROLE_ADMIN, ROLE_ANALYST, ROLE_VIEWER)
    write_requires_analyst = True

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied("Authentication is required.")
        if not request.user.is_superuser and getattr(request.user, "role", None) not in self.allowed_roles:
            raise PermissionDenied("Your role is not authorized for this action.")
        if (
            self.write_requires_analyst
            and request.method not in SAFE_METHODS
            and not is_analyst(request.user)
        ):
            raise PermissionDenied("Your role has read-only access.")
        return super().dispatch(request, *args, **kwargs)


class AdminOnlyMixin(RolePermissionMixin):
    allowed_roles = (ROLE_ADMIN,)


def json_error(message, status=400, **extra):
    payload = {"success": False, "error": message}
    payload.update(extra)
    return JsonResponse(payload, status=status)
