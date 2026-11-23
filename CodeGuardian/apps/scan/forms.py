from django import forms

from .models import Scan
from .services import validate_upload


class ScanUploadForm(forms.Form):
    name = forms.CharField(max_length=200, required=False)
    source_file = forms.FileField(label="Source file or ZIP project")

    def clean_source_file(self):
        uploaded = self.cleaned_data["source_file"]
        validate_upload(uploaded)
        uploaded.seek(0)
        return uploaded

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        return name or "Untitled security scan"
