from django.contrib import admin

from .models import InvestigationCase, InvestigationNote

admin.site.register(InvestigationCase)
admin.site.register(InvestigationNote)
