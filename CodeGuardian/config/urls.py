from django.contrib import admin
from django.urls import include, path

from apps.core import views as core_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls", namespace="accounts")),
    path("scan/", include("apps.scan.urls", namespace="scan")),
    path("reports/", include("apps.reports.urls", namespace="reports")),
    path("", include("apps.core.urls", namespace="core")),
    path("api/v1/", include("apps.core.api_urls", namespace="api")),
]

handler403 = core_views.error_403
handler404 = core_views.error_404
handler500 = core_views.error_500
