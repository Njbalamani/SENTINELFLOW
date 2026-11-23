from django.contrib import admin

from .models import Finding, Scan, ScanFile


@admin.register(Scan)
class ScanAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "status", "total_vulnerabilities", "security_score", "created_at")
    list_filter = ("status", "source_type")
    search_fields = ("name", "original_filename")


@admin.register(ScanFile)
class ScanFileAdmin(admin.ModelAdmin):
    list_display = ("relative_path", "scan", "language", "size_bytes", "line_count")
    search_fields = ("relative_path",)


@admin.register(Finding)
class FindingAdmin(admin.ModelAdmin):
    list_display = ("rule_id", "severity", "file_path", "line", "scan")
    list_filter = ("severity", "detector", "category")
    search_fields = ("rule_id", "title", "file_path")
