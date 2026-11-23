from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.api import IsReadOnlyForViewer, restrict_to_self
from apps.monitoring.services import is_off_hours
from .models import ActivitySource, UserSession, UserActivity


class UserActivitySerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    classification = serializers.SerializerMethodField()
    risk_score = serializers.SerializerMethodField()

    class Meta:
        model = UserActivity
        fields = (
            "id", "user", "username", "activity_type", "timestamp", "ip_address", "user_agent",
            "resource", "action_detail", "bytes_transferred", "session_key", "is_off_hours",
            "is_unusual_location", "source", "metadata", "classification", "risk_score",
        )
        read_only_fields = ("id", "username", "classification", "risk_score")

    def get_classification(self, obj):
        return getattr(getattr(obj, "detection", None), "classification", None)

    def get_risk_score(self, obj):
        detection = getattr(obj, "detection", None)
        return detection.risk_score if detection else None


class ActivityIngestSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = UserActivity
        fields = (
            "id", "user", "activity_type", "timestamp", "resource", "action_detail",
            "bytes_transferred", "ip_address", "is_unusual_location", "source", "metadata",
        )

    def validate_bytes_transferred(self, value):
        if value < 0:
            raise serializers.ValidationError("Byte count cannot be negative.")
        return value

    def validate_resource(self, value):
        if len(value) > 512:
            raise serializers.ValidationError("Resource path is too long.")
        return value


class UserSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSession
        fields = "__all__"


class ActivityViewSet(viewsets.ModelViewSet):
    serializer_class = UserActivitySerializer
    permission_classes = [IsReadOnlyForViewer]

    def get_serializer_class(self):
        if self.action == "create":
            return ActivityIngestSerializer
        return UserActivitySerializer

    def get_queryset(self):
        qs = UserActivity.objects.select_related("user", "detection").all()
        qs = restrict_to_self(self, qs)
        params = self.request.query_params
        if params.get("activity_type"):
            qs = qs.filter(activity_type=params["activity_type"])
        if params.get("user"):
            qs = qs.filter(user_id=params["user"])
        if params.get("days"):
            from datetime import timedelta

            from django.utils import timezone

            try:
                qs = qs.filter(timestamp__gte=timezone.now() - timedelta(days=int(params["days"])))
            except ValueError:
                pass
        return qs.order_by("-timestamp")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        activity = serializer.save(
            source=ActivitySource.API,
            is_off_hours=is_off_hours(serializer.validated_data.get("timestamp")),
        )
        from apps.detection.services import analyze_activity

        analyze_activity(activity)
        output = UserActivitySerializer(activity, context={"request": request})
        return Response(output.data, status=status.HTTP_201_CREATED, headers=self.get_success_headers(output.data))

    @action(detail=True, methods=["post"], url_path="reanalyze")
    def reanalyze(self, request, pk=None):
        from apps.detection.services import analyze_activity

        result = analyze_activity(self.get_object())
        return Response({"detail": "Activity re-analysed.", "classification": result.classification,
                         "risk_score": result.risk_score})
