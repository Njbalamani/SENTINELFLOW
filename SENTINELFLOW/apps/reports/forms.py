from django import forms
from django.contrib.auth import get_user_model

from apps.alerts.models import SecurityAlert
from apps.investigation.models import InvestigationCase
from apps.reports.models import GeneratedReport


class ReportGenerateForm(forms.Form):
    report_type = forms.ChoiceField(choices=GeneratedReport.ReportType.choices)
    alert = forms.ModelChoiceField(queryset=SecurityAlert.objects.all(), required=False)
    user = forms.ModelChoiceField(queryset=get_user_model().objects.all(), required=False)
    case = forms.ModelChoiceField(queryset=InvestigationCase.objects.all(), required=False)
    days = forms.IntegerField(min_value=1, max_value=90, initial=14)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
        self.fields["alert"].widget.attrs["data-report-field"] = "ALERT"
        self.fields["user"].widget.attrs["data-report-field"] = "ACTIVITY"
        self.fields["case"].widget.attrs["data-report-field"] = "INVESTIGATION"
        self.fields["days"].widget.attrs["data-report-field"] = "ACTIVITY"

    def clean(self):
        cleaned = super().clean()
        kind = cleaned.get("report_type")
        requirements = {
            GeneratedReport.ReportType.ALERT: "alert",
            GeneratedReport.ReportType.ACTIVITY: "user",
            GeneratedReport.ReportType.INVESTIGATION: "case",
        }
        field = requirements.get(kind)
        if field and not cleaned.get(field):
            self.add_error(field, f"This field is required for a {kind.lower()} report.")
        return cleaned
