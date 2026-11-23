from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("recommendations/", views.RecommendationsView.as_view(), name="recommendations"),
    path("health/", views.HealthView.as_view(), name="health"),
]
