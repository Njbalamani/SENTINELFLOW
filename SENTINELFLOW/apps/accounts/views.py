from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import CreateView, ListView, TemplateView, View

from apps.core.middleware import _client_ip
from apps.core.models import log_audit
from apps.core.permissions import AdminOnlyMixin
from apps.monitoring.services import record_failed_login, record_login, record_logout
from .forms import ProfileForm, SentinelLoginForm, UserRegistrationForm
from .models import User


class SentinelLoginView(LoginView):
    template_name = "auth/login.html"
    form_class = SentinelLoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        user = form.get_user()
        if not user.is_active:
            form.add_error(None, "This account has been deactivated.")
            return self.form_invalid(form)
        login(self.request, user)
        remember = form.cleaned_data.get("remember_me")
        self.request.session.set_expiry(60 * 60 * 24 * 14 if remember else 0)
        record_login(user, self.request)
        messages.success(self.request, f"Welcome back, {user.display_name}.")
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        username = form.data.get("username", "").strip()
        if username:
            record_failed_login(username, self.request)
            log_audit(
                action="DENIED", entity_type="LOGIN_ATTEMPT", entity_id=username,
                ip_address=_client_ip(self.request), path=self.request.path,
                details={"reason": "invalid credentials"},
            )
        messages.error(self.request, "Invalid username or password. The attempt has been logged.")
        return super().form_invalid(form)

    def get_success_url(self):
        target = self.request.POST.get("next") or self.request.GET.get("next")
        if target and url_has_allowed_host_and_scheme(target, allowed_hosts={self.request.get_host()}, require_https=self.request.is_secure()):
            return target
        return str(reverse_lazy("dashboard:home"))


class SentinelLogoutView(View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            record_logout(request.user, request)
        logout(request)
        messages.info(request, "You have been signed out securely.")
        return redirect("accounts:login")


class RegistrationView(AdminOnlyMixin, CreateView):
    template_name = "auth/register.html"
    form_class = UserRegistrationForm
    success_url = reverse_lazy("accounts:users")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Register User"
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        log_audit(
            action="CREATE", entity_type="USER", entity_id=self.object.pk, actor=self.request.user,
            details={"username": self.object.username, "role": self.object.role},
        )
        messages.success(self.request, f"Account created for {self.object.username}.")
        return response


class UserListView(AdminOnlyMixin, ListView):
    model = User
    template_name = "accounts/user_list.html"
    context_object_name = "users"
    paginate_by = 25

    def get_queryset(self):
        return User.objects.select_related("risk_profile").all().order_by("username")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "User Management"
        return ctx


class UserStatusView(AdminOnlyMixin, View):
    http_method_names = ["post"]

    def post(self, request, pk, *args, **kwargs):
        target = User.objects.filter(pk=pk).first()
        if not target:
            messages.error(request, "User not found.")
        elif target.pk == request.user.pk:
            messages.error(request, "You cannot deactivate your own account.")
        else:
            target.is_active = target.is_active is False
            target.save(update_fields=["is_active"])
            log_audit(
                action="UPDATE", entity_type="USER", entity_id=target.pk, actor=request.user,
                details={"is_active": target.is_active},
            )
            messages.success(request, f"Account for {target.username} is now {'active' if target.is_active else 'disabled'}.")
        return redirect("accounts:users")


class ProfileView(TemplateView):
    template_name = "accounts/profile.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "My Profile"
        ctx["form"] = kwargs.get("form") or ProfileForm(instance=self.request.user)
        ctx["profile"] = getattr(self.request.user, "risk_profile", None)
        return ctx

    def post(self, request, *args, **kwargs):
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect("accounts:profile")
        messages.error(request, "Please correct the errors below.")
        return self.render_to_response(self.get_context_data(form=form))
