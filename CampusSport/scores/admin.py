from django.contrib import admin
from .models import Score, TeamScore, ClassPoints


@admin.register(Score)
class ScoreAdmin(admin.ModelAdmin):
    list_display = ['registration', 'stage', 'result', 'rank', 'points', 'recorded_by']
    list_filter = ['stage', 'registration__event__sports_meet']


@admin.register(TeamScore)
class TeamScoreAdmin(admin.ModelAdmin):
    list_display = ['team_registration', 'stage', 'result', 'rank', 'points']


@admin.register(ClassPoints)
class ClassPointsAdmin(admin.ModelAdmin):
    list_display = ['sports_meet', 'class_name', 'total_points', 'gold_medals', 'rank']
    list_filter = ['sports_meet']
