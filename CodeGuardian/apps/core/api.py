from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import Serializer
from rest_framework.views import APIView
from rest_framework.response import Response

from apps.core.recommendations import RECOMMENDATIONS
from apps.core.services import dashboard_metrics
from apps.reports.api import GeneratedReportViewSet
from apps.scan.api import FindingViewSet, ScanFileViewSet, ScanViewSet


class DashboardSummarySerializer(Serializer):
    pass


class DashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        metrics = dashboard_metrics(request.user)
        metrics["recent_scans"] = [
            {
                "id": str(item.id),
                "name": item.name,
                "status": item.status,
                "score": item.security_score,
                "total_vulnerabilities": item.total_vulnerabilities,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in metrics["recent_scans"]
        ]
        return Response(metrics)


class RecommendationsView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DashboardSummarySerializer

    def get_queryset(self):
        return RECOMMENDATIONS

    def list(self, request, *args, **kwargs):
        return Response(RECOMMENDATIONS)


__all__ = [
    "DashboardSummaryView",
    "RecommendationsView",
    "ScanViewSet",
    "FindingViewSet",
    "ScanFileViewSet",
    "GeneratedReportViewSet",
]
