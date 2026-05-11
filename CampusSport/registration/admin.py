from django.contrib import admin
from .models import Student, Registration, TeamRegistration


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['name', 'gender', 'class_name', 'grade', 'student_id']
    list_filter = ['gender', 'class_name', 'grade']
    search_fields = ['name', 'student_id']


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ['student', 'event', 'status', 'lane', 'submitted_by', 'created_at']
    list_filter = ['status', 'event__sports_meet']
    search_fields = ['student__name']


@admin.register(TeamRegistration)
class TeamRegistrationAdmin(admin.ModelAdmin):
    list_display = ['class_name', 'event', 'status', 'submitted_by']
    list_filter = ['status']
