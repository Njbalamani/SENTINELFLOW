from django.urls import path

from .views import AlertDetailView, AlertListView

app_name = "alerts"

urlpatterns = [
    path("", AlertListView.as_view(), name="list"),
    path("<int:pk>/", AlertDetailView.as_view(), name="detail"),
]
