from django.contrib import admin

from .models import UserActivity, UserSession

admin.site.register(UserActivity)
admin.site.register(UserSession)
