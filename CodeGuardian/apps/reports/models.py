from django.conf import settings
from django.db import models


class GeneratedReport(models.Model):
    class Format(models.TextChoices):
        PDF = "PDF", "PDF"
        JSON = "JSON", "JSON"

    scan = models.ForeignKey("scan.Scan", on_delete=models.CASCADE, related_name="reports")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports")
    format = models.CharField(max_length=10, choices=Format.choices)
    file = models.FileField(upload_to="reports/", blank=True)
    filename = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["-created_at"])]

    def __str__(self):
        return self.filename
