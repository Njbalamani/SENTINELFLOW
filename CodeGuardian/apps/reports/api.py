from rest_framework import serializers, viewsets

from apps.core.permissions import IsOwnerOrAdmin
from .models import GeneratedReport


class GeneratedReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeneratedReport
        fields = ("id", "scan", "format", "filename", "file", "created_at")
        read_only_fields = fields


class GeneratedReportViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = GeneratedReportSerializer
    permission_classes = [IsOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        queryset = GeneratedReport.objects.all() if user.is_superuser else GeneratedReport.objects.filter(owner=user)
        return queryset.select_related("scan")
