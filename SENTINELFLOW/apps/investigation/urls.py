from django.urls import path

from .views import CaseCreateView, CaseDetailView, CaseListView

app_name = "investigation"

urlpatterns = [
    path("", CaseListView.as_view(), name="list"),
    path("new/", CaseCreateView.as_view(), name="create"),
    path("<int:pk>/", CaseDetailView.as_view(), name="detail"),
]
