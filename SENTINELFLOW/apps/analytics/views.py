from django.views.generic import TemplateView

from apps.core.permissions import RolePermissionMixin
from . import services


class DashboardView(RolePermissionMixin, TemplateView):
    template_name = "dashboard/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        days = self.request.GET.get("days", "14")
        try:
            days = min(90, max(7, int(days)))
        except (TypeError, ValueError):
            days = 14
        stats = services.dashboard_stats(days)
        ctx.update(
            {
                "page_title": "Security Overview",
                "stats": stats,
                "days": days,
                "chart_data": {
                    "activity": services.daily_activity(days),
                    "risk": services.risk_distribution(),
                    "severity": services.alerts_by_severity(),
                },
                "top_users": services.top_risky_users(),
                "recent_alerts": services.recent_alerts(),
            }
        )
        return ctx


class AnalyticsView(RolePermissionMixin, TemplateView):
    template_name = "dashboard/analytics.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        days = self.request.GET.get("days", "14")
        try:
            days = min(90, max(7, int(days)))
        except (TypeError, ValueError):
            days = 14
        ctx.update(
            {
                "page_title": "Behavioural Analytics",
                "stats": services.dashboard_stats(days),
                "days": days,
                "chart_data": {
                    "activity": services.daily_activity(days),
                    "risk": services.risk_distribution(),
                    "severity": services.alerts_by_severity(),
                    "types": services.activity_breakdown(days),
                },
                "top_users": services.top_risky_users(12),
            }
        )
        return ctx
