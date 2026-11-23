from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics import services
from apps.core.api import IsSecurityStaff


class AnalyticsSummaryView(APIView):
    """All dashboard metrics are computed from live database queries."""

    permission_classes = [IsSecurityStaff]

    def get(self, request, *args, **kwargs):
        try:
            days = min(90, max(7, int(request.query_params.get("days", 14))))
        except (TypeError, ValueError):
            days = 14
        return Response({
            "stats": {key: value if not hasattr(value, "pk") else value.model_name
                      for key, value in services.dashboard_stats(days).items()},
            "daily_activity": services.daily_activity(days),
            "risk_distribution": services.risk_distribution(),
            "alerts_by_severity": services.alerts_by_severity(),
            "activity_breakdown": services.activity_breakdown(days),
            "top_risky_users": services.top_risky_users(),
        })
