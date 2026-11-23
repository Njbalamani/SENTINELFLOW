from django.urls import path

from .views import (
    ProfileView, RegistrationView, SentinelLoginView, SentinelLogoutView,
    UserListView, UserStatusView,
)

app_name = "accounts"

urlpatterns = [
    path("login/", SentinelLoginView.as_view(), name="login"),
    path("logout/", SentinelLogoutView.as_view(), name="logout"),
    path("register/", RegistrationView.as_view(), name="register"),
    path("users/", UserListView.as_view(), name="users"),
    path("users/<int:pk>/toggle/", UserStatusView.as_view(), name="user-toggle"),
    path("profile/", ProfileView.as_view(), name="profile"),
]
