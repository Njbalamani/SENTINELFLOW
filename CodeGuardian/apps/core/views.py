from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View

from .recommendations import RECOMMENDATIONS
from .services import dashboard_metrics


class DashboardView(LoginRequiredMixin, View):
    template_name = "core/dashboard.html"

    def get(self, request):
        return render(request, self.template_name, {"metrics": dashboard_metrics(request.user)})


class RecommendationsView(LoginRequiredMixin, View):
    template_name = "core/recommendations.html"

    def get(self, request):
        return render(request, self.template_name, {"recommendations": RECOMMENDATIONS})


class HealthView(View):
    def get(self, request):
        from django.db import connection

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            database = "ok"
        except Exception:
            database = "unavailable"
        return JsonResponse({"status": "ok", "database": database})


def error_403(request, exception=None):
    return render(request, "core/error.html", {"code": 403, "message": "Access denied."}, status=403)


def error_404(request, exception=None):
    return render(request, "core/error.html", {"code": 404, "message": "Page not found."}, status=404)


def error_500(request):
    return render(request, "core/error.html", {"code": 500, "message": "Something went wrong."}, status=500)
