from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    organization = forms.CharField(max_length=150, required=False)

    class Meta:
        model = User
        fields = ("username", "email", "organization", "password1", "password2")


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("email", "organization", "bio", "plan")
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 4}),
        }
