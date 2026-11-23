from django.contrib import admin
from django.urls import include, path

from apps.core import views as core_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls", namespace="core")),
    path("accounts/", include("apps.accounts.urls", namespace="accounts")),
    path("dashboard/", include("apps.analytics.urls", namespace="dashboard")),
    path("monitoring/", include("apps.monitoring.urls", namespace="monitoring")),
    path("detection/", include("apps.detection.urls", namespace="detection")),
    path("alerts/", include("apps.alerts.urls", namespace="alerts")),
    path("investigations/", include("apps.investigation.urls", namespace="investigation")),
    path("reports/", include("apps.reports.urls", namespace="reports")),
    path("api/v1/", include("apps.core.api_urls", namespace="api")),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    path("health/", core_views.health_check, name="health-check"),
    path("", core_views.home_redirect, name="home"),
    path("403/", core_views.access_denied, name="access-denied"),
    path("404/", core_views.not_found, name="not-found"),
    path("500/", core_views.server_error, name="server-error"),
]

handler403 = "apps.core.views.access_denied"
handler404 = "apps.core.views.not_found"
handler500 = "apps.core.views.server_error"
