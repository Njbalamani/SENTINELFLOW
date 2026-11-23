from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render

from apps.core.models import AuditLog
from apps.core.permissions import AdminOnlyMixin
from django.views.generic import ListView


def home_redirect(request):
    if request.user.is_authenticated:
        return redirect("dashboard:home")
    return redirect("accounts:login")


def health_check(request):
    from django.db import connection

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return JsonResponse({"status": "ok", "database": "ok"})
    except Exception as exc:
        return JsonResponse({"status": "error", "detail": str(exc)}, status=503)


@login_required
def access_denied(request, exception=None):
    return render(request, "core/error.html", {
        "code": 403,
        "title": "Access denied",
        "message": "You do not have permission to view this resource.",
    }, status=403)


def not_found(request, exception=None):
    return render(request, "core/error.html", {
        "code": 404,
        "title": "Page not found",
        "message": "The resource you requested does not exist.",
    }, status=404)


def server_error(request):
    return render(request, "core/error.html", {
        "code": 500,
        "title": "Something went wrong",
        "message": "An unexpected error occurred. Please try again later.",
    }, status=500)


class AuditLogListView(AdminOnlyMixin, ListView):
    model = AuditLog
    template_name = "core/audit.html"
    context_object_name = "logs"
    paginate_by = 40

    def get_queryset(self):
        qs = AuditLog.objects.select_related("actor").all()
        action = self.request.GET.get("action", "").strip()
        if action:
            qs = qs.filter(action=action)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Audit Trail"
        ctx["actions"] = AuditLog.Action.choices
        return ctx
