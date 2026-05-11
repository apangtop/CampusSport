from django.contrib import admin
from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['sports_meet', 'report_type', 'file_format', 'created_at']
    list_filter = ['report_type', 'file_format']
