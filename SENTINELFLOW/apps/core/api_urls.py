from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.alerts.api import AlertViewSet
from apps.analytics.api import AnalyticsSummaryView
from apps.accounts.api import UserSerializer
from apps.detection.api import DetectionViewSet, ModelRunViewSet, RiskProfileViewSet
from apps.investigation.api import InvestigationViewSet
from apps.monitoring.api import ActivityViewSet
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.generics import ListAPIView

from apps.accounts.models import User

app_name = "api"

router = DefaultRouter()
router.register("activities", ActivityViewSet, basename="activity")
router.register("detections", DetectionViewSet, basename="detection")
router.register("risk-profiles", RiskProfileViewSet, basename="riskprofile")
router.register("alerts", AlertViewSet, basename="alert")
router.register("investigations", InvestigationViewSet, basename="investigation")
router.register("models", ModelRunViewSet, basename="model")


class UserListView(ListAPIView):
    serializer_class = UserSerializer
    queryset = User.objects.all()

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("username"):
            qs = qs.filter(username__icontains=self.request.query_params["username"])
        return qs.order_by("username")


urlpatterns = [
    path("auth/token/", ObtainAuthToken.as_view(), name="token"),
    path("analytics/summary/", AnalyticsSummaryView.as_view(), name="analytics-summary"),
    path("users/", UserListView.as_view(), name="user-list"),
    path("", include(router.urls)),
]
