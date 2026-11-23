from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ("SENTINELFLOW profile", {"fields": ("role", "employee_id", "department", "job_title", "phone")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("SENTINELFLOW profile", {"fields": ("role", "department", "email")}),
    )
    list_display = ("username", "email", "role", "department", "employee_id", "is_active", "last_login")
    list_filter = ("role", "department", "is_active", "is_staff")
    search_fields = ("username", "email", "employee_id", "first_name", "last_name")
