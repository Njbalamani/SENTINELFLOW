from django.urls import include, path
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.routers import DefaultRouter

from apps.core.api import DashboardSummaryView, RecommendationsView
from apps.reports.api import GeneratedReportViewSet
from apps.scan.api import FindingViewSet, ScanFileViewSet, ScanViewSet

app_name = "api"

router = DefaultRouter()
router.register("scans", ScanViewSet, basename="scan")
router.register("findings", FindingViewSet, basename="finding")
router.register("files", ScanFileViewSet, basename="scanfile")
router.register("reports", GeneratedReportViewSet, basename="report")

urlpatterns = [
    path("auth/token/", ObtainAuthToken.as_view(), name="token"),
    path("analytics/summary/", DashboardSummaryView.as_view(), name="analytics-summary"),
    path("recommendations/", RecommendationsView.as_view(), name="recommendations"),
    path("", include(router.urls)),
]
