from django import forms

from .models import CasePriority, CaseStatus, InvestigationCase, InvestigationNote


class CaseCreateForm(forms.ModelForm):
    class Meta:
        model = InvestigationCase
        fields = ("title", "subject", "priority", "activities", "findings")
        widgets = {
            "activities": forms.CheckboxSelectMultiple(),
            "findings": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs["class"] = "form-control" if name != "activities" else "activity-checks"


class CaseUpdateForm(forms.ModelForm):
    class Meta:
        model = InvestigationCase
        fields = ("status", "priority", "findings", "conclusion")
        widgets = {
            "findings": forms.Textarea(attrs={"rows": 4}),
            "conclusion": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"


class CaseNoteForm(forms.ModelForm):
    class Meta:
        model = InvestigationNote
        fields = ("note",)
        widgets = {"note": forms.Textarea(attrs={"rows": 3, "placeholder": "Add case note..."})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["note"].widget.attrs["class"] = "form-control"
