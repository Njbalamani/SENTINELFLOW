from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.CodeGuardianLoginView.as_view(), name="login"),
    path("logout/", views.CodeGuardianLogoutView.as_view(), name="logout"),
    path("register/", views.RegistrationView.as_view(), name="register"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
]
