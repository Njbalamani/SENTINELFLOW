from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.models import User
from .models import ActivitySource, ActivityType, UserActivity


class ActivityFilterForm(forms.Form):
    activity_type = forms.ChoiceField(required=False, choices=[("", "All activity types"), *ActivityType.choices])
    user_id = forms.ModelChoiceField(required=False, queryset=User.objects.all(), label="User", empty_label="All users")
    date_from = forms.DateTimeField(required=False, widget=forms.DateTimeInput(attrs={"type": "datetime-local"}))
    date_to = forms.DateTimeField(required=False, widget=forms.DateTimeInput(attrs={"type": "datetime-local"}))
    search = forms.CharField(required=False, max_length=120)

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("date_from"), cleaned.get("date_to")
        if start and end and start > end:
            raise ValidationError("The start date must be before the end date.")
        return cleaned


class ActivityCreateForm(forms.ModelForm):
    timestamp = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
        initial=timezone.now,
    )

    class Meta:
        model = UserActivity
        fields = (
            "user", "activity_type", "timestamp", "resource", "action_detail",
            "bytes_transferred", "ip_address", "is_unusual_location", "source",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (css + " form-control").strip()
        self.fields["source"].initial = ActivitySource.SYNTHETIC
