from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView

from apps.core.audit import audit_action
from .forms import ProfileForm, RegistrationForm
from .models import User


class CodeGuardianLoginView(SuccessMessageMixin, LoginView):
    template_name = "auth/login.html"
    success_message = "Welcome back to CodeGuardian."
    redirect_authenticated_user = True


class CodeGuardianLogoutView(LogoutView):
    http_method_names = ["post", "options"]


class RegistrationView(SuccessMessageMixin, CreateView):
    form_class = RegistrationForm
    template_name = "auth/register.html"
    success_url = reverse_lazy("accounts:login")
    success_message = "Account created. You can now sign in."

    def form_valid(self, form):
        response = super().form_valid(form)
        audit_action(self.request, "REGISTER", "User", str(form.instance.pk))
        return response


class ProfileView(SuccessMessageMixin, UpdateView):
    form_class = ProfileForm
    template_name = "accounts/profile.html"
    success_url = reverse_lazy("accounts:profile")
    success_message = "Profile updated."

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        response = super().form_valid(form)
        audit_action(self.request, "UPDATE_PROFILE", "User", str(form.instance.pk))
        return response
