from django.contrib import admin

from .models import DetectionModelRun, DetectionResult, UserRiskProfile

admin.site.register(DetectionResult)
admin.site.register(UserRiskProfile)
admin.site.register(DetectionModelRun)
