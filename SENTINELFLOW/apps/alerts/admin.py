from django.contrib import admin

from .models import AlertNote, SecurityAlert

admin.site.register(SecurityAlert)
admin.site.register(AlertNote)
