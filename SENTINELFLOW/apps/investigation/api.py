from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.api import IsReadOnlyForViewer, restrict_to_self
from apps.core.models import log_audit
from .models import InvestigationCase, InvestigationNote
from .services import add_note, close_case


class InvestigationNoteSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = InvestigationNote
        fields = ("id", "case", "author", "author_name", "note", "created_at")
        read_only_fields = ("id", "author", "author_name", "created_at")


class InvestigationCaseSerializer(serializers.ModelSerializer):
    short_id = serializers.CharField(read_only=True)
    notes = InvestigationNoteSerializer(many=True, read_only=True)

    class Meta:
        model = InvestigationCase
        fields = (
            "id", "case_id", "short_id", "title", "alert", "subject", "status", "priority",
            "assigned_to", "opened_by", "activities", "findings", "conclusion", "notes",
            "created_at", "updated_at", "closed_at",
        )
        read_only_fields = ("id", "case_id", "short_id", "opened_by", "notes", "created_at", "updated_at", "closed_at")


class InvestigationViewSet(viewsets.ModelViewSet):
    serializer_class = InvestigationCaseSerializer
    permission_classes = [IsReadOnlyForViewer]

    def get_queryset(self):
        qs = InvestigationCase.objects.select_related("subject", "assigned_to", "alert").all()
        qs = restrict_to_self(self, qs, user_field="subject")
        status = self.request.query_params.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(opened_by=self.request.user, assigned_to=self.request.user)
        log_audit(action="CREATE", entity_type="INVESTIGATION_CASE", actor=self.request.user)

    @action(detail=True, methods=["post"])
    def note(self, request, pk=None):
        text = str(request.data.get("note", "")).strip()
        if not text:
            return Response({"error": "Note cannot be empty."}, status=400)
        entry = add_note(self.get_object(), request.user, text)
        return Response(InvestigationNoteSerializer(entry).data, status=201)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        case = close_case(
            self.get_object(), actor=request.user, conclusion=request.data.get("conclusion", "")
        )
        return Response({"detail": "Case closed.", "status": case.status})
