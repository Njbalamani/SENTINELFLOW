from rest_framework import serializers, viewsets

from apps.core.api import restrict_to_self
from .models import DetectionModelRun, DetectionResult, UserRiskProfile


class DetectionResultSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = DetectionResult
        fields = (
            "id", "activity", "user", "username", "model_name", "classification", "risk_score",
            "anomaly_score", "confidence", "reasons", "features", "models_agreed", "created_at",
        )
        read_only_fields = fields


class UserRiskProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    department = serializers.CharField(source="user.get_department_display", read_only=True)

    class Meta:
        model = UserRiskProfile
        fields = (
            "id", "user", "username", "department", "risk_score", "risk_level", "total_activities",
            "suspicious_count", "critical_count", "failed_logins_24h", "downloads_24h",
            "last_activity_at", "last_calculated",
        )
        read_only_fields = fields


class ModelRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetectionModelRun
        fields = (
            "id", "model_name", "samples", "accuracy", "weighted_f1",
            "artifact_path", "notes", "is_active", "trained_at",
        )
        read_only_fields = fields


class DetectionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DetectionResultSerializer

    def get_queryset(self):
        qs = DetectionResult.objects.select_related("user", "activity").all()
        qs = restrict_to_self(self, qs)
        classification = self.request.query_params.get("classification")
        if classification:
            qs = qs.filter(classification=classification)
        return qs.order_by("-created_at")


class RiskProfileViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserRiskProfileSerializer

    def get_queryset(self):
        return UserRiskProfile.objects.select_related("user").order_by("-risk_score")


class ModelRunViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ModelRunSerializer
    queryset = DetectionModelRun.objects.all()
