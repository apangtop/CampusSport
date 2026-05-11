import math
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
    def score_summary(self, request, pk=None):
        """各项目成绩录入完成度汇总"""
        meet = self.get_object()
        stage = request.query_params.get('stage', 'final')
        from registration.models import Registration
        from scores.models import Score
        events = meet.events.all()
        data = []
        for ev in events:
            total = Registration.objects.filter(
                event=ev, status='approved'
            ).count()
            scored = Score.objects.filter(
                registration__event=ev, stage=stage
            ).count()
            data.append({
                'event_id': ev.id,
                'event_name': ev.name,
                'total': total,
                'scored': scored,
                'complete': total > 0 and scored >= total
            })
        return Response(data)

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
        user = self.request.user
        if user.role == 'referee':
            qs = qs.filter(referee=user, sports_meet__status='ongoing')
        meet_id = self.request.query_params.get('sports_meet')
        if meet_id:
            qs = qs.filter(sports_meet_id=meet_id)
        event_type = self.request.query_params.get('type')
        if event_type:
            qs = qs.filter(event_type=event_type)
        reg_status = self.request.query_params.get('reg_status')
        if reg_status:
            qs = qs.filter(registrations__status=reg_status).distinct()
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
        """自动分组 + 分配道次（按项目类型采用不同策略）"""
        event = self.get_object()
        from registration.models import Registration, TeamRegistration
        from collections import defaultdict
        lanes_per_group = int(request.data.get('lanes_per_group', 6))
        stage = request.data.get('stage', 'preliminary')

        is_team = event.event_type in ('relay', 'team_confrontation')

        if is_team:
            # ── 团体项目：按班级排道次 ──
            teams = list(TeamRegistration.objects.filter(
                event=event, status='approved'
            ).order_by('class_name'))

            if not teams:
                return Response({'detail': '没有已审核的团体报名'}, status=status.HTTP_400_BAD_REQUEST)

            TeamRegistration.objects.filter(event=event, status='approved').update(schedule=None, lane=None)
            schedule, _ = Schedule.objects.get_or_create(
                event=event, stage=stage, group_number=1,
                defaults={'notes': '自动创建'}
            )
            for lane, t in enumerate(teams, 1):
                t.schedule = schedule
                t.lane = lane
                t.save(update_fields=['schedule', 'lane'])

            return Response({
                'detail': f'团体项目排序完成：{len(teams)} 队按班级排列'
            })

        # ── 个人项目 ──
        registrations = list(Registration.objects.filter(
            event=event, status='approved'
        ).select_related('student'))

        if not registrations:
            return Response({'detail': '没有已审核的报名记录'}, status=status.HTTP_400_BAD_REQUEST)

        # 清除旧分配
        Registration.objects.filter(event=event, status='approved').update(schedule=None, lane=None)

        # 班级交替排列：每个班轮流出一个人，相邻选手不同班
        class_groups = defaultdict(list)
        for r in registrations:
            class_groups[r.student.class_name].append(r)
        ordered = []
        class_names = sorted(class_groups.keys())
        while any(class_groups.values()):
            for cls in class_names:
                if class_groups[cls]:
                    ordered.append(class_groups[cls].pop(0))

        is_track = event.event_type == 'track'

        if is_track:
            # ── 径赛：分组 + 分道 ──
            num_groups = max(1, math.ceil(len(ordered) / lanes_per_group))
            groups_info = []
            for group_num in range(1, num_groups + 1):
                schedule, _ = Schedule.objects.get_or_create(
                    event=event, stage=stage, group_number=group_num,
                    defaults={'notes': '自动创建'}
                )
                start_idx = (group_num - 1) * lanes_per_group
                group_regs = ordered[start_idx:start_idx + lanes_per_group]
                for lane, reg in enumerate(group_regs, 1):
                    reg.schedule = schedule
                    reg.lane = lane
                    reg.save(update_fields=['schedule', 'lane'])
                groups_info.append({
                    'group': group_num,
                    'count': len(group_regs),
                    'classes': [r.student.class_name for r in group_regs]
                })
            return Response({
                'detail': f'径赛分组完成：{len(ordered)} 人 → {num_groups} 组（每组 ≤ {lanes_per_group} 道），相邻跑道不同班',
                'groups': groups_info
            })
        else:
            # ── 田赛/趣味：只排出场顺序，无道次 ──
            schedule, _ = Schedule.objects.get_or_create(
                event=event, stage=stage, group_number=1,
                defaults={'notes': '自动创建'}
            )
            for order, reg in enumerate(ordered, 1):
                reg.schedule = schedule
                reg.lane = order  # lane 复用为出场序号
                reg.save(update_fields=['schedule', 'lane'])
            return Response({
                'detail': f'出场顺序排定：{len(ordered)} 人（班级交替排列）',
                'order': [f'{r.student.name}({r.student.class_name})' for r in ordered[:20]]
            })


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
