from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError

from .models import DEPARTMENTS, ROLE_ANALYST, ROLE_VIEWER, ROLE_CHOICES, User


class StyledFormMixin:
    """Applies the shared input styling to every widget."""

    def apply_styles(self):
        for field in self.fields.values():
            css = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (css + " form-control").strip()
            field.widget.attrs.setdefault("autocomplete", "off")


class SentinelLoginForm(StyledFormMixin, AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={"placeholder": "Username", "autocomplete": "username"})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Password", "autocomplete": "current-password"})
    )
    remember_me = forms.BooleanField(required=False, widget=forms.CheckboxInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styles()
        self.fields["remember_me"].widget.attrs["class"] = "form-check-input"


class UserRegistrationForm(StyledFormMixin, UserCreationForm):
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(
        choices=tuple(choice for choice in ROLE_CHOICES if choice[0] != "ADMIN"),
        initial=ROLE_VIEWER,
    )
    department = forms.ChoiceField(choices=DEPARTMENTS, initial="OTHER")
    employee_id = forms.CharField(max_length=32, required=False)
    job_title = forms.CharField(max_length=120, required=False)

    class Meta:
        model = User
        fields = (
            "username", "email", "first_name", "last_name", "role",
            "department", "employee_id", "job_title", "password1", "password2",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styles()
        for name in ("first_name", "last_name"):
            self.fields[name].required = False

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("A user with this email address already exists.")
        return email

    def clean_employee_id(self):
        value = self.cleaned_data.get("employee_id", "").strip()
        if value and User.objects.filter(employee_id=value).exists():
            raise ValidationError("This employee ID is already assigned.")
        return value or None

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.role = self.cleaned_data.get("role", ROLE_VIEWER)
        user.employee_id = self.cleaned_data.get("employee_id")
        if commit:
            user.save()
        return user


class ProfileForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "department", "job_title", "phone")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styles()

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError("A user with this email address already exists.")
        return email
