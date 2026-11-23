from django.contrib import admin

from .models import GeneratedReport


@admin.register(GeneratedReport)
class GeneratedReportAdmin(admin.ModelAdmin):
    list_display = ("filename", "scan", "owner", "format", "created_at")
    list_filter = ("format",)
    search_fields = ("filename",)
