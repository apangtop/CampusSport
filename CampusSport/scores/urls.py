from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ScoreViewSet, TeamScoreViewSet, ClassPointsViewSet

router = DefaultRouter()
router.register('scores', ScoreViewSet, basename='score')
router.register('team-scores', TeamScoreViewSet, basename='team-score')
router.register('class-points', ClassPointsViewSet, basename='class-points')

urlpatterns = [
    path('', include(router.urls)),
]
