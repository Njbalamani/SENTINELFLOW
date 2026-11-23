from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView

from apps.core.permissions import AdminOnlyMixin, RolePermissionMixin
from apps.detection.services import analyze_activity
from apps.monitoring.services import is_off_hours
from .forms import ActivityCreateForm, ActivityFilterForm
from .models import ActivitySource, UserActivity


class ActivityListView(RolePermissionMixin, ListView):
    model = UserActivity
    template_name = "monitoring/activity_list.html"
    context_object_name = "activities"
    paginate_by = 25

    def get_queryset(self):
        qs = UserActivity.objects.select_related("user", "detection").all()
        if self.request.user.role == "VIEWER" and not self.request.user.is_superuser:
            qs = qs.filter(user=self.request.user)
        self.filter_form = ActivityFilterForm(self.request.GET)
        if self.filter_form.is_valid():
            data = self.filter_form.cleaned_data
            if data.get("activity_type"):
                qs = qs.filter(activity_type=data["activity_type"])
            if data.get("user_id"):
                qs = qs.filter(user=data["user_id"])
            if data.get("date_from"):
                qs = qs.filter(timestamp__gte=data["date_from"])
            if data.get("date_to"):
                qs = qs.filter(timestamp__lte=data["date_to"])
            if data.get("search"):
                qs = qs.filter(
                    resource__icontains=data["search"]
                ) | qs.filter(action_detail__icontains=data["search"]) | qs.filter(user__username__icontains=data["search"])
        return qs.order_by("-timestamp")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Activity Monitor"
        ctx["filter_form"] = getattr(self, "filter_form", ActivityFilterForm())
        ctx["activity_types"] = UserActivity._meta.get_field("activity_type").choices
        return ctx


class ActivityDetailView(RolePermissionMixin, DetailView):
    model = UserActivity
    template_name = "monitoring/activity_detail.html"
    context_object_name = "activity"

    def get_queryset(self):
        qs = UserActivity.objects.select_related("user", "detection")
        if self.request.user.role == "VIEWER" and not self.request.user.is_superuser:
            return qs.filter(user=self.request.user)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = f"Activity #{self.object.pk}"
        ctx["detection"] = getattr(self.object, "detection", None)
        return ctx


class ActivityCreateView(AdminOnlyMixin, CreateView):
    model = UserActivity
    form_class = ActivityCreateForm
    template_name = "monitoring/activity_form.html"
    success_url = reverse_lazy("monitoring:list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Record Activity"
        return ctx

    def form_valid(self, form):
        activity = form.save(commit=False)
        activity.is_off_hours = is_off_hours(activity.timestamp)
        activity.source = activity.source or ActivitySource.SYNTHETIC
        activity.save()
        try:
            analyze_activity(activity)
        except Exception:
            messages.warning(self.request, "Activity saved, but automated analysis could not be completed.")
        else:
            messages.success(self.request, "Activity recorded and analysed successfully.")
        return super().form_valid(form)
