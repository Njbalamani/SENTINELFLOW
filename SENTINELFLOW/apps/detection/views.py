from django.db.models import Q
from django.views.generic import DetailView, ListView, TemplateView

from apps.core.permissions import AdminOnlyMixin, RolePermissionMixin
from .models import Classification, DetectionModelRun, DetectionResult, UserRiskProfile
from apps.analytics.services import incident_timeline


class DetectionListView(RolePermissionMixin, ListView):
    model = DetectionResult
    template_name = "detection/detection_list.html"
    context_object_name = "results"
    paginate_by = 25

    def get_queryset(self):
        qs = DetectionResult.objects.select_related("user", "activity").all()
        if self.request.user.role == "VIEWER" and not self.request.user.is_superuser:
            qs = qs.filter(user=self.request.user)
        classification = self.request.GET.get("classification", "").strip()
        search = self.request.GET.get("search", "").strip()
        if classification:
            qs = qs.filter(classification=classification)
        if search:
            qs = qs.filter(Q(user__username__icontains=search) | Q(activity__resource__icontains=search))
        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "AI Detection Results"
        ctx["classifications"] = Classification.choices
        ctx["selected"] = self.request.GET.get("classification", "")
        return ctx


class DetectionDetailView(RolePermissionMixin, DetailView):
    model = DetectionResult
    template_name = "detection/detection_detail.html"
    context_object_name = "result"

    def get_queryset(self):
        qs = DetectionResult.objects.select_related("user", "activity")
        if self.request.user.role == "VIEWER" and not self.request.user.is_superuser:
            return qs.filter(user=self.request.user)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = f"Detection #{self.object.pk}"
        ctx["alerts"] = self.object.alerts.select_related("user").all()
        return ctx


class RiskProfileListView(RolePermissionMixin, ListView):
    model = UserRiskProfile
    template_name = "detection/risk_list.html"
    context_object_name = "profiles"
    paginate_by = 25

    def get_queryset(self):
        qs = UserRiskProfile.objects.select_related("user").all()
        level = self.request.GET.get("level", "").strip()
        if level:
            qs = qs.filter(risk_level=level)
        return qs.order_by("-risk_score")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "User Risk Profiles"
        ctx["levels"] = UserRiskProfile._meta.get_field("risk_level").choices
        return ctx


class RiskProfileDetailView(RolePermissionMixin, DetailView):
    model = UserRiskProfile
    template_name = "detection/risk_detail.html"
    context_object_name = "profile"

    def get_queryset(self):
        return UserRiskProfile.objects.select_related("user")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = f"Risk profile — {self.object.user.display_name}"
        ctx["timeline"] = incident_timeline(self.object.user)
        ctx["alerts"] = self.object.user.alerts.select_related("user").order_by("-created_at")[:10]
        ctx["detections"] = self.object.user.detections.select_related("activity").order_by("-created_at")[:10]
        return ctx


class ModelInfoView(AdminOnlyMixin, TemplateView):
    template_name = "detection/model_info.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Detection Models"
        ctx["runs"] = DetectionModelRun.objects.all()
        from ml.predict import load_models

        models = load_models()
        ctx["metadata"] = models["metadata"] if models else None
        ctx["artifact_dir"] = str(settings_dir())
        return ctx


def settings_dir():
    from django.conf import settings

    return settings.ML_ARTIFACT_DIR
