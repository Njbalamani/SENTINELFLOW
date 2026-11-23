from django.urls import path

from .views import AnalyticsView, DashboardView

app_name = "dashboard"

urlpatterns = [
    path("", DashboardView.as_view(), name="home"),
    path("analytics/", AnalyticsView.as_view(), name="analytics"),
]
