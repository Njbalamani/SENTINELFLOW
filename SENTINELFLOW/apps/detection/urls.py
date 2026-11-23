from django.urls import path

from .views import (
    DetectionDetailView, DetectionListView, ModelInfoView,
    RiskProfileDetailView, RiskProfileListView,
)

app_name = "detection"

urlpatterns = [
    path("", DetectionListView.as_view(), name="list"),
    path("<int:pk>/", DetectionDetailView.as_view(), name="detail"),
    path("risk/", RiskProfileListView.as_view(), name="risk-list"),
    path("risk/<int:pk>/", RiskProfileDetailView.as_view(), name="risk-detail"),
    path("models/", ModelInfoView.as_view(), name="models"),
]
