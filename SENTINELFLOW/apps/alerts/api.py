from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.api import IsReadOnlyForViewer, restrict_to_self
from .models import AlertNote, SecurityAlert
from .services import change_status


class AlertNoteSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = AlertNote
        fields = ("id", "alert", "author", "author_name", "note", "created_at")
        read_only_fields = ("id", "author", "author_name", "created_at")


class SecurityAlertSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    notes = AlertNoteSerializer(many=True, read_only=True)

    class Meta:
        model = SecurityAlert
        fields = (
            "id", "title", "description", "severity", "status", "user", "username", "activity",
            "detection", "assigned_to", "risk_score", "evidence", "resolution_notes", "notes",
            "created_at", "updated_at", "resolved_at",
        )
        read_only_fields = ("id", "username", "notes", "created_at", "updated_at", "resolved_at")

    def validate_status(self, value):
        if value not in SecurityAlert.Status.values:
            raise serializers.ValidationError("Unsupported alert status.")
        return value


class AlertViewSet(viewsets.ModelViewSet):
    serializer_class = SecurityAlertSerializer
    permission_classes = [IsReadOnlyForViewer]

    def get_queryset(self):
        qs = SecurityAlert.objects.select_related("user", "assigned_to", "detection").all()
        qs = restrict_to_self(self, qs)
        params = self.request.query_params
        if params.get("severity"):
            qs = qs.filter(severity=params["severity"])
        if params.get("status"):
            qs = qs.filter(status=params["status"])
        return qs.order_by("-created_at")

    @action(detail=True, methods=["post"], url_path="status")
    def status_update(self, request, pk=None):
        alert = self.get_object()
        status = request.data.get("status", "")
        if status not in SecurityAlert.Status.values:
            return Response({"error": "Invalid status."}, status=400)
        change_status(
            alert, status, actor=request.user,
            notes=request.data.get("notes", ""),
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return Response(SecurityAlertSerializer(alert).data)

    @action(detail=True, methods=["post"])
    def note(self, request, pk=None):
        alert = self.get_object()
        text = str(request.data.get("note", "")).strip()
        if not text:
            return Response({"error": "Note cannot be empty."}, status=400)
        entry = AlertNote.objects.create(alert=alert, author=request.user, note=text[:4000])
        return Response(AlertNoteSerializer(entry).data, status=201)

    @action(detail=True, methods=["post"])
    def investigate(self, request, pk=None):
        from apps.investigation.services import create_case_from_alert

        case, created = create_case_from_alert(self.get_object(), actor=request.user)
        return Response({"case_id": case.pk, "short_id": case.short_id, "created": created}, status=201 if created else 200)
