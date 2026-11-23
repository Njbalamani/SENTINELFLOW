from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    organization = models.CharField(max_length=150, blank=True)
    plan = models.CharField(max_length=40, default="DEVELOPER")
    bio = models.TextField(blank=True, max_length=1000)

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.username
