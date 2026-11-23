from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import SuspiciousOperation, ValidationError
from django.urls import reverse_lazy
from django.views.generic import DetailView, FormView, ListView

from apps.core.audit import audit_action
from apps.core.permissions import OwnerRequiredMixin
from .forms import ScanUploadForm
from .models import Finding, Scan
from .services import process_upload, run_scan


class ScanListView(LoginRequiredMixin, ListView):
    model = Scan
    template_name = "scan/list.html"
    context_object_name = "scans"
    paginate_by = 15

    def get_queryset(self):
        queryset = Scan.objects.all() if self.request.user.is_superuser else Scan.objects.filter(owner=self.request.user)
        return queryset.select_related("owner").prefetch_related("findings")


class ScanCreateView(LoginRequiredMixin, FormView):
    form_class = ScanUploadForm
    template_name = "scan/upload.html"
    success_url = reverse_lazy("scan:list")

    def form_valid(self, form):
        uploaded = form.cleaned_data["source_file"]
        scan = Scan(
            owner=self.request.user,
            name=form.cleaned_data["name"],
            original_filename=uploaded.name[:255],
        )
        try:
            process_upload(scan, uploaded)
            run_scan(scan)
        except (ValidationError, SuspiciousOperation) as exc:
            scan.status = Scan.Status.FAILED
            scan.error_message = str(exc)
            scan.save()
            messages.error(self.request, str(exc))
            return self.form_invalid(form)
        audit_action(self.request, "CREATE_SCAN", "Scan", str(scan.id), {"status": scan.status})
        messages.success(
            self.request,
            f"Scan complete: {scan.total_vulnerabilities} findings, security score {scan.security_score}.",
        )
        return super().form_valid(form)

    def get_success_url(self):
        latest = Scan.objects.filter(owner=self.request.user).order_by("-created_at").first()
        return reverse_lazy("scan:result", kwargs={"pk": latest.pk}) if latest else self.success_url


class ScanDetailView(LoginRequiredMixin, OwnerRequiredMixin, DetailView):
    model = Scan
    template_name = "scan/result.html"
    context_object_name = "scan"

    def get_queryset(self):
        return Scan.objects.prefetch_related("files", "findings")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["findings"] = self.object.findings.all()
        context["severity_counts"] = self.object.severity_counts()
        context["max_size"] = settings.CODEGUARDIAN["MAX_FILE_SIZE_MB"]
        return context
