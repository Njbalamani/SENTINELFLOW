from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic import DetailView, ListView

from apps.core.middleware import _client_ip
from apps.core.permissions import RolePermissionMixin
from apps.investigation.services import create_case_from_alert
from .forms import AlertFilterForm, AlertNoteForm, AlertStatusForm
from .models import SecurityAlert
from .services import change_status


class AlertListView(RolePermissionMixin, ListView):
    model = SecurityAlert
    template_name = "alerts/alert_list.html"
    context_object_name = "alerts"
    paginate_by = 25

    def get_queryset(self):
        qs = SecurityAlert.objects.select_related("user", "detection", "assigned_to").all()
        if self.request.user.role == "VIEWER" and not self.request.user.is_superuser:
            qs = qs.filter(user=self.request.user)
        self.filter_form = AlertFilterForm(self.request.GET)
        if self.filter_form.is_valid():
            data = self.filter_form.cleaned_data
            if data.get("severity"):
                qs = qs.filter(severity=data["severity"])
            if data.get("status"):
                qs = qs.filter(status=data["status"])
            if data.get("search"):
                qs = qs.filter(title__icontains=data["search"]) | qs.filter(user__username__icontains=data["search"])
        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Security Alerts"
        ctx["filter_form"] = getattr(self, "filter_form", AlertFilterForm())
        return ctx


class AlertDetailView(RolePermissionMixin, DetailView):
    model = SecurityAlert
    template_name = "alerts/alert_detail.html"
    context_object_name = "alert"

    def get_queryset(self):
        qs = SecurityAlert.objects.select_related("user", "activity", "detection", "assigned_to")
        if self.request.user.role == "VIEWER" and not self.request.user.is_superuser:
            return qs.filter(user=self.request.user)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = f"Alert #{self.object.pk}"
        ctx["status_form"] = AlertStatusForm(instance=self.object)
        ctx["note_form"] = AlertNoteForm()
        ctx["notes"] = self.object.notes.select_related("author").all()
        ctx["case"] = getattr(self.object, "investigation", None)
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        action = request.POST.get("action", "update")
        if action == "investigate":
            case, created = create_case_from_alert(self.object, actor=request.user)
            messages.success(request, f"Investigation case {case.short_id} {'created' if created else 'already exists'}.")
            return redirect("investigation:detail", pk=case.pk)
        if action == "note":
            form = AlertNoteForm(request.POST)
            if form.is_valid():
                note = form.save(commit=False)
                note.alert = self.object
                note.author = request.user
                note.save()
                messages.success(request, "Investigation note added.")
            else:
                messages.error(request, "Note cannot be empty.")
            return redirect("alerts:detail", pk=self.object.pk)
        form = AlertStatusForm(request.POST, instance=self.object)
        if form.is_valid():
            change_status(
                self.object, form.cleaned_data["status"], actor=request.user,
                notes=form.cleaned_data.get("resolution_notes", ""), ip_address=_client_ip(request),
            )
            messages.success(request, "Alert status updated.")
        else:
            messages.error(request, "Invalid status update.")
        return redirect("alerts:detail", pk=self.object.pk)
