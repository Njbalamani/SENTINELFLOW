from django import forms

from .models import AlertNote, AlertStatus, SecurityAlert, Severity


class AlertFilterForm(forms.Form):
    severity = forms.ChoiceField(required=False, choices=[("", "All severities"), *Severity.choices])
    status = forms.ChoiceField(required=False, choices=[("", "All statuses"), *AlertStatus.choices])
    search = forms.CharField(required=False, max_length=120)


class AlertStatusForm(forms.ModelForm):
    class Meta:
        model = SecurityAlert
        fields = ("status", "resolution_notes")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
        self.fields["resolution_notes"].widget.attrs["rows"] = 3


class AlertNoteForm(forms.ModelForm):
    class Meta:
        model = AlertNote
        fields = ("note",)
        widgets = {"note": forms.Textarea(attrs={"rows": 3, "placeholder": "Add investigation note..."})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["note"].widget.attrs["class"] = "form-control"
