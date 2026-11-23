from django.urls import path

from . import views

app_name = "scan"

urlpatterns = [
    path("", views.ScanListView.as_view(), name="list"),
    path("upload/", views.ScanCreateView.as_view(), name="upload"),
    path("result/<uuid:pk>/", views.ScanDetailView.as_view(), name="result"),
]
