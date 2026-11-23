from rest_framework import serializers, status, viewsets
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.audit import audit_action
from apps.core.permissions import IsOwnerOrAdmin
from .models import Finding, Scan, ScanFile
from .services import process_upload, run_scan


class ScanFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScanFile
        fields = ("id", "relative_path", "language", "size_bytes", "line_count")


class FindingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Finding
        fields = (
            "id", "rule_id", "title", "severity", "category", "owasp", "file_path",
            "line", "column", "code_snippet", "description", "impact", "remediation",
            "corrected_code", "confidence", "detector", "explanation_source", "created_at",
        )


class ScanSerializer(serializers.ModelSerializer):
    files = ScanFileSerializer(many=True, read_only=True)
    findings = FindingSerializer(many=True, read_only=True)
    severity_counts = serializers.SerializerMethodField()

    class Meta:
        model = Scan
        fields = (
            "id", "name", "status", "source_type", "original_filename", "files_scanned",
            "lines_scanned", "total_vulnerabilities", "security_score", "tool_versions",
            "error_message", "created_at", "completed_at", "files", "findings", "severity_counts",
        )
        read_only_fields = fields

    def get_severity_counts(self, obj):
        return obj.severity_counts()


class ScanCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, required=False)
    source_file = serializers.FileField()


class ScanViewSet(viewsets.ModelViewSet):
    serializer_class = ScanSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    parser_classes = [MultiPartParser, FormParser]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        queryset = Scan.objects.all() if user.is_superuser else Scan.objects.filter(owner=user)
        return queryset.prefetch_related("files", "findings").order_by("-created_at")

    def create(self, request, *args, **kwargs):
        incoming = ScanCreateSerializer(data=request.data)
        incoming.is_valid(raise_exception=True)
        uploaded = incoming.validated_data["source_file"]
        scan = Scan(
            owner=request.user,
            name=incoming.validated_data.get("name") or "API security scan",
            original_filename=uploaded.name[:255],
        )
        try:
            process_upload(scan, uploaded)
            run_scan(scan)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        audit_action(request, "API_CREATE_SCAN", "Scan", str(scan.id), {"status": scan.status})
        return Response(ScanSerializer(scan).data, status=status.HTTP_201_CREATED)


class FindingViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FindingSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        queryset = Finding.objects.filter(scan__owner=user)
        if user.is_superuser:
            queryset = Finding.objects.all()
        scan_id = self.request.query_params.get("scan")
        if scan_id:
            queryset = queryset.filter(scan_id=scan_id)
        severity = self.request.query_params.get("severity")
        if severity:
            queryset = queryset.filter(severity=severity.upper())
        return queryset.select_related("scan", "source_file").order_by("-severity", "file_path", "line")


class ScanFileViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ScanFileSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        queryset = ScanFile.objects.filter(scan__owner=user)
        if user.is_superuser:
            queryset = ScanFile.objects.all()
        return queryset.select_related("scan")
