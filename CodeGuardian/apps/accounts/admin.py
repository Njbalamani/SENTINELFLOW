from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CodeGuardianUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("CodeGuardian", {"fields": ("organization", "plan", "bio")}),
    )
    list_display = ("username", "email", "organization", "plan", "is_staff")
