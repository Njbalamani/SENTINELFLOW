from django.urls import path

from .views import ReportCreateView, ReportDownloadView, ReportListView

app_name = "reports"

urlpatterns = [
    path("", ReportListView.as_view(), name="list"),
    path("generate/", ReportCreateView.as_view(), name="generate"),
    path("download/<int:pk>/", ReportDownloadView.as_view(), name="download"),
]
