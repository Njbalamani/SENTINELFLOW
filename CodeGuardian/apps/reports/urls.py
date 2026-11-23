from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("", views.ReportListView.as_view(), name="list"),
    path("generate/pdf/<uuid:pk>/", views.GeneratePdfReportView.as_view(), name="generate-pdf"),
    path("generate/json/<uuid:pk>/", views.GenerateJsonReportView.as_view(), name="generate-json"),
    path("download/<int:pk>/", views.DownloadReportView.as_view(), name="download"),
    path("export/<uuid:pk>/", views.ExportJsonView.as_view(), name="export-json"),
]
