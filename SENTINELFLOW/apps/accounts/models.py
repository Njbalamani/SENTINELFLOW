from django.contrib.auth.models import AbstractUser
from django.db import models

ROLE_ADMIN = "ADMIN"
ROLE_ANALYST = "ANALYST"
ROLE_VIEWER = "VIEWER"

ROLE_CHOICES = (
    (ROLE_ADMIN, "Administrator"),
    (ROLE_ANALYST, "Security Analyst"),
    (ROLE_VIEWER, "Viewer"),
)

DEPARTMENTS = (
    ("ENGINEERING", "Engineering"),
    ("FINANCE", "Finance"),
    ("HUMAN_RESOURCES", "Human Resources"),
    ("OPERATIONS", "Operations"),
    ("SALES", "Sales"),
    ("IT", "Information Technology"),
    ("LEGAL", "Legal"),
    ("OTHER", "Other"),
)


class User(AbstractUser):
    role = models.CharField(max_length=16, choices=ROLE_CHOICES, default=ROLE_VIEWER, db_index=True)
    employee_id = models.CharField(max_length=32, unique=True, null=True, blank=True)
    department = models.CharField(max_length=32, choices=DEPARTMENTS, default="OTHER")
    job_title = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=32, blank=True)

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"

    @property
    def is_admin_role(self):
        return self.role == ROLE_ADMIN or self.is_superuser

    @property
    def is_security_staff(self):
        return self.role in {ROLE_ADMIN, ROLE_ANALYST} or self.is_superuser

    @property
    def display_name(self):
        return self.get_full_name() or self.username
