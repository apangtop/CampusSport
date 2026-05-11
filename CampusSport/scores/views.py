from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum
from .models import Score, TeamScore, ConfrontationRound, ClassPoints
from .serializers import ScoreSerializer, TeamScoreSerializer, ConfrontationRoundSerializer, ClassPointsSerializer
from events.models import Event
from registration.models import Registration


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'


class IsAdminOrReferee(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['admin', 'referee']


def calculate_rank_and_points(event, stage='final'):
    """重新计算某项目某阶段的排名和积分"""
    scores = Score.objects.filter(
        registration__event=event,
        stage=stage,
        result_numeric__isnull=False
    )

    # 根据项目类型决定排序方向
    descending_types = ['field', 'fun_individual']
    if event.event_type in descending_types and event.result_unit in ['meter', 'count']:
        scores = scores.order_by('-result_numeric')
    else:
        scores = scores.order_by('result_numeric')

    score_rules = event.score_rules or {1: 7, 2: 5, 3: 4, 4: 3, 5: 2, 6: 1}
    for idx, score in enumerate(scores, 1):
        score.rank = idx
        score.points = float(score_rules.get(str(idx), score_rules.get(idx, 0))) * event.score_multiplier
        score.save(update_fields=['rank', 'points'])

    return scores.count()


def recalculate_class_points(sports_meet):
    """重新计算班级总积分"""
    class_points_map = {}

    for score in Score.objects.filter(
        registration__event__sports_meet=sports_meet,
        stage='final',
        points__gt=0
    ).select_related('registration__student', 'registration__event'):
        class_name = score.registration.student.class_name
        if class_name not in class_points_map:
            class_points_map[class_name] = {'total': 0, 'gold': 0, 'silver': 0, 'bronze': 0}
        class_points_map[class_name]['total'] += score.points
        if score.rank == 1:
            class_points_map[class_name]['gold'] += 1
        elif score.rank == 2:
            class_points_map[class_name]['silver'] += 1
        elif score.rank == 3:
            class_points_map[class_name]['bronze'] += 1

    for team_score in TeamScore.objects.filter(
        team_registration__event__sports_meet=sports_meet,
        stage='final',
        points__gt=0
    ).select_related('team_registration'):
        class_name = team_score.team_registration.class_name
        if class_name not in class_points_map:
            class_points_map[class_name] = {'total': 0, 'gold': 0, 'silver': 0, 'bronze': 0}
        class_points_map[class_name]['total'] += team_score.points
        if team_score.rank == 1:
            class_points_map[class_name]['gold'] += 1
        elif team_score.rank == 2:
            class_points_map[class_name]['silver'] += 1
        elif team_score.rank == 3:
            class_points_map[class_name]['bronze'] += 1

    sorted_classes = sorted(class_points_map.items(), key=lambda x: x[1]['total'], reverse=True)
    for rank, (class_name, data) in enumerate(sorted_classes, 1):
        ClassPoints.objects.update_or_create(
            sports_meet=sports_meet,
            class_name=class_name,
            defaults={
                'total_points': data['total'],
                'gold_medals': data['gold'],
                'silver_medals': data['silver'],
                'bronze_medals': data['bronze'],
                'rank': rank,
            }
        )


class ScoreViewSet(viewsets.ModelViewSet):
    queryset = Score.objects.select_related(
        'registration__student', 'registration__event', 'recorded_by'
    ).all()
    serializer_class = ScoreSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.role == 'referee':
            qs = qs.filter(registration__event__referee=user)
        elif user.role == 'teacher':
            qs = qs.filter(registration__student__class_name=user.class_name)

        event_id = self.request.query_params.get('event')
        if event_id:
            qs = qs.filter(registration__event_id=event_id)
        stage = self.request.query_params.get('stage')
        if stage:
            qs = qs.filter(stage=stage)
        meet_id = self.request.query_params.get('sports_meet')
        if meet_id:
            qs = qs.filter(registration__event__sports_meet_id=meet_id)
        class_name = self.request.query_params.get('class_name')
        if class_name:
            qs = qs.filter(registration__student__class_name=class_name)
        return qs

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update']:
            return [IsAdminOrReferee()]
        if self.action == 'destroy':
            return [IsAdmin()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(recorded_by=self.request.user)

    def perform_update(self, serializer):
        instance = serializer.save()
        event = instance.registration.event
        calculate_rank_and_points(event, instance.stage)
        recalculate_class_points(event.sports_meet)

    @action(detail=False, methods=['post'], permission_classes=[IsAdminOrReferee])
    def batch_submit(self, request):
        """批量提交成绩"""
        scores_data = request.data.get('scores', [])
        results = []
        for item in scores_data:
            try:
                reg = Registration.objects.get(id=item['registration_id'])
                stage = item.get('stage', 'final')
                result = item.get('result', '')
                result_numeric = item.get('result_numeric')

                score, created = Score.objects.update_or_create(
                    registration=reg,
                    stage=stage,
                    defaults={
                        'result': result,
                        'result_numeric': result_numeric,
                        'recorded_by': request.user
                    }
                )
                results.append({'registration_id': reg.id, 'status': 'ok'})
            except Registration.DoesNotExist:
                results.append({'registration_id': item.get('registration_id'), 'status': 'not_found'})

        if results:
            try:
                first_event = Registration.objects.get(
                    id=scores_data[0]['registration_id']
                ).event
                stage = scores_data[0].get('stage', 'final')
                calculate_rank_and_points(first_event, stage)
                recalculate_class_points(first_event.sports_meet)
            except Exception:
                pass

        return Response({'results': results})

    @action(detail=False, methods=['post'], permission_classes=[IsAdmin])
    def calculate_ranks(self, request):
        """手动触发排名计算"""
        event_id = request.data.get('event_id')
        stage = request.data.get('stage', 'final')
        try:
            event = Event.objects.get(id=event_id)
        except Event.DoesNotExist:
            return Response({'detail': '项目不存在'}, status=status.HTTP_404_NOT_FOUND)
        count = calculate_rank_and_points(event, stage)
        recalculate_class_points(event.sports_meet)
        return Response({'detail': f'已计算 {count} 条成绩的排名'})

    @action(detail=False, methods=['post'], permission_classes=[IsAdmin])
    def confirm_advancement(self, request):
        """确认晋级名单"""
        event_id = request.data.get('event_id')
        advanced_registration_ids = request.data.get('registration_ids', [])
        Score.objects.filter(
            registration__event_id=event_id, stage='preliminary'
        ).update(is_advanced=False)
        Score.objects.filter(
            registration_id__in=advanced_registration_ids, stage='preliminary'
        ).update(is_advanced=True)
        return Response({'detail': '晋级名单已确认'})


class TeamScoreViewSet(viewsets.ModelViewSet):
    queryset = TeamScore.objects.select_related('team_registration__event').prefetch_related('rounds').all()
    serializer_class = TeamScoreSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update']:
            return [IsAdminOrReferee()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        event_id = self.request.query_params.get('event')
        if event_id:
            qs = qs.filter(team_registration__event_id=event_id)
        return qs


class ClassPointsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ClassPoints.objects.all()
    serializer_class = ClassPointsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        meet_id = self.request.query_params.get('sports_meet')
        if meet_id:
            qs = qs.filter(sports_meet_id=meet_id)
        return qs.order_by('rank')

    @action(detail=False, methods=['post'], permission_classes=[IsAdmin])
    def recalculate(self, request):
        meet_id = request.data.get('sports_meet_id')
        from events.models import SportsMeet
        try:
            meet = SportsMeet.objects.get(id=meet_id)
        except SportsMeet.DoesNotExist:
            return Response({'detail': '运动会不存在'}, status=status.HTTP_404_NOT_FOUND)
        recalculate_class_points(meet)
        return Response({'detail': '积分已重新计算'})
