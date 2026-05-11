from django.contrib import admin
from .models import SportsMeet, Event, Schedule


@admin.register(SportsMeet)
class SportsMeetAdmin(admin.ModelAdmin):
    list_display = ['name', 'session', 'status', 'start_date', 'end_date']
    list_filter = ['status']


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['name', 'sports_meet', 'event_type', 'gender', 'referee']
    list_filter = ['event_type', 'gender', 'sports_meet']


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ['event', 'stage', 'group_number', 'scheduled_time', 'venue']
    list_filter = ['stage']
