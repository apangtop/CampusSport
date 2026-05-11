from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SportsMeetViewSet, EventViewSet, ScheduleViewSet
from .history_views import (
    HistoryMeetListView, HistoryPointsView,
    HistoryEventBestView, StudentHistoryView
)

router = DefaultRouter()
router.register('sports-meets', SportsMeetViewSet, basename='sportsmeet')
router.register('events', EventViewSet, basename='event')
router.register('schedules', ScheduleViewSet, basename='schedule')

urlpatterns = [
    path('', include(router.urls)),
    path('history/meets/', HistoryMeetListView.as_view(), name='history-meets'),
    path('history/points/', HistoryPointsView.as_view(), name='history-points'),
    path('history/event-best/', HistoryEventBestView.as_view(), name='history-event-best'),
    path('history/student/', StudentHistoryView.as_view(), name='history-student'),
]
