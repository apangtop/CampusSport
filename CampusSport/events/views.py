from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import SportsMeet, Event, Schedule
from .serializers import (
    SportsMeetSerializer, SportsMeetDetailSerializer,
    EventSerializer, EventListSerializer, ScheduleSerializer
)


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'


class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        return request.user.is_authenticated and request.user.role == 'admin'


class SportsMeetViewSet(viewsets.ModelViewSet):
    queryset = SportsMeet.objects.all()
    permission_classes = [IsAdminOrReadOnly]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return SportsMeetDetailSerializer
        return SportsMeetSerializer

    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def set_status(self, request, pk=None):
        meet = self.get_object()
        new_status = request.data.get('status')
        valid_statuses = [s[0] for s in SportsMeet.STATUS_CHOICES]
        if new_status not in valid_statuses:
            return Response({'detail': '无效状态'}, status=status.HTTP_400_BAD_REQUEST)
        meet.status = new_status
        meet.save()
        return Response(SportsMeetSerializer(meet).data)

    @action(detail=True, methods=['get'])
    def schedule_overview(self, request, pk=None):
        """赛程总览"""
        meet = self.get_object()
        events = meet.events.prefetch_related('schedules').all()
        data = []
        for event in events:
            for sch in event.schedules.all():
                data.append({
                    'event_id': event.id,
                    'event_name': event.name,
                    'stage': sch.get_stage_display(),
                    'group_number': sch.group_number,
                    'scheduled_time': sch.scheduled_time,
                    'venue': sch.venue,
                    'referee': event.referee.real_name if event.referee else '',
                })
        return Response(data)


class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.select_related('sports_meet', 'referee').all()
    permission_classes = [IsAdminOrReadOnly]

    def get_serializer_class(self):
        if self.action == 'list':
            return EventListSerializer
        return EventSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        meet_id = self.request.query_params.get('sports_meet')
        if meet_id:
            qs = qs.filter(sports_meet_id=meet_id)
        event_type = self.request.query_params.get('type')
        if event_type:
            qs = qs.filter(event_type=event_type)
        return qs

    @action(detail=True, methods=['get'])
    def participants(self, request, pk=None):
        """获取项目参赛名单"""
        event = self.get_object()
        from registration.models import Registration
        from registration.serializers import RegistrationDetailSerializer
        registrations = Registration.objects.filter(
            event=event, status__in=['submitted', 'approved']
        ).select_related('student', 'schedule')
        serializer = RegistrationDetailSerializer(registrations, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def auto_assign_lanes(self, request, pk=None):
        """自动分配道次"""
        event = self.get_object()
        from registration.models import Registration
        registrations = Registration.objects.filter(
            event=event, status='approved'
        ).order_by('id')
        for idx, reg in enumerate(registrations, 1):
            reg.lane = idx
            reg.save(update_fields=['lane'])
        return Response({'detail': f'已为 {registrations.count()} 名参赛者分配道次'})


class ScheduleViewSet(viewsets.ModelViewSet):
    queryset = Schedule.objects.select_related('event').all()
    permission_classes = [IsAdminOrReadOnly]

    def get_serializer_class(self):
        return ScheduleSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        event_id = self.request.query_params.get('event')
        if event_id:
            qs = qs.filter(event_id=event_id)
        meet_id = self.request.query_params.get('sports_meet')
        if meet_id:
            qs = qs.filter(event__sports_meet_id=meet_id)
        return qs
