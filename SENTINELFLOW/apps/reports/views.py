from django.contrib import messages
from django.http import FileResponse, Http404
from django.views.generic import DetailView, FormView, ListView

from apps.core.permissions import RolePermissionMixin
from .forms import ReportGenerateForm
from .models import GeneratedReport
from .services import generate_report


class ReportListView(RolePermissionMixin, ListView):
    model = GeneratedReport
    template_name = "reports/report_list.html"
    context_object_name = "reports"
    paginate_by = 25

    def get_queryset(self):
        return GeneratedReport.objects.select_related("generated_by").all()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Security Reports"
        return ctx


class ReportCreateView(RolePermissionMixin, FormView):
    template_name = "reports/report_form.html"
    form_class = ReportGenerateForm

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Generate Report"
        return ctx

    def form_valid(self, form):
        data = form.cleaned_data
        try:
            report = generate_report(
                data["report_type"], generated_by=self.request.user,
                alert=data.get("alert"), user=data.get("user"), case=data.get("case"), days=data.get("days", 14),
            )
            messages.success(self.request, f"Report generated: {report.title}")
            return redirect_report(report.pk)
        except ValueError as exc:
            messages.error(self.request, str(exc))
            return self.form_invalid(form)
        except RuntimeError as exc:
            messages.error(self.request, str(exc))
            return self.form_invalid(form)
        except Exception as exc:
            messages.error(self.request, f"Report generation failed: {exc}")
            return self.form_invalid(form)


def redirect_report(pk):
    from django.shortcuts import redirect
    from django.urls import reverse

    return redirect(reverse("reports:list"))


class ReportDownloadView(RolePermissionMixin, DetailView):
    model = GeneratedReport

    def get(self, request, *args, **kwargs):
        report = self.get_object()
        if not report.file or not report.file.storage.exists(report.file.name):
            raise Http404("The report file is no longer available.")
        return FileResponse(
            report.file.open("rb"), content_type="application/pdf",
            as_attachment=True, filename=f"{report.title[:60].replace(' ', '_')}.pdf",
        )
