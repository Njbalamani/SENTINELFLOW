from django.urls import path

from .views import ActivityCreateView, ActivityDetailView, ActivityListView

app_name = "monitoring"

urlpatterns = [
    path("", ActivityListView.as_view(), name="list"),
    path("new/", ActivityCreateView.as_view(), name="create"),
    path("<int:pk>/", ActivityDetailView.as_view(), name="detail"),
]
