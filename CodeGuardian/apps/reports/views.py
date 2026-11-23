from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import FileResponse, Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.views.generic import ListView

from apps.core.audit import audit_action
from apps.core.permissions import OwnerRequiredMixin
from apps.scan.models import Scan
from .models import GeneratedReport
from .pdf import create_pdf_report
from .services import create_json_report, json_download_response


class ReportListView(LoginRequiredMixin, ListView):
    model = GeneratedReport
    template_name = "reports/list.html"
    context_object_name = "reports"
    paginate_by = 15

    def get_queryset(self):
        queryset = GeneratedReport.objects.all() if self.request.user.is_superuser else GeneratedReport.objects.filter(owner=self.request.user)
        return queryset.select_related("scan")


class GeneratePdfReportView(LoginRequiredMixin, OwnerRequiredMixin, View):
    def post(self, request, pk):
        scan = Scan.objects.get(pk=pk)
        if scan.owner != request.user and not request.user.is_superuser:
            raise Http404()
        report = create_pdf_report(scan, request.user)
        audit_action(request, "GENERATE_PDF_REPORT", "GeneratedReport", str(report.id))
        messages.success(request, "PDF report generated.")
        return redirect("reports:list")


class GenerateJsonReportView(LoginRequiredMixin, View):
    def post(self, request, pk):
        scan = Scan.objects.get(pk=pk)
        if scan.owner != request.user and not request.user.is_superuser:
            raise Http404()
        report = create_json_report(scan, request.user)
        audit_action(request, "GENERATE_JSON_REPORT", "GeneratedReport", str(report.id))
        messages.success(request, "JSON export generated.")
        return redirect("reports:list")


class DownloadReportView(LoginRequiredMixin, View):
    def get(self, request, pk):
        report = GeneratedReport.objects.filter(pk=pk).first()
        if not report:
            raise Http404()
        if report.owner != request.user and not request.user.is_superuser:
            raise Http404()
        if not report.file:
            raise Http404()
        return FileResponse(report.file.open("rb"), as_attachment=True, filename=report.filename)


class ExportJsonView(LoginRequiredMixin, View):
    def get(self, request, pk):
        scan = Scan.objects.filter(pk=pk).first()
        if not scan:
            raise Http404()
        if scan.owner != request.user and not request.user.is_superuser:
            raise Http404()
        return json_download_response(scan)
