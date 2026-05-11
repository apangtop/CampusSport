from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.db.models import Sum
from .models import Score, TeamScore, ConfrontationRound, ClassPoints
from .serializers import ScoreSerializer, TeamScoreSerializer, ConfrontationRoundSerializer, ClassPointsSerializer
from events.models import Event, Schedule
from registration.models import Registration


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'


class IsAdminOrReferee(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['admin', 'referee']


def calculate_rank_and_points(event, stage='final'):
    """重新计算某项目某阶段的排名和积分"""
    from django.db import transaction
    with transaction.atomic():
        scores = Score.objects.select_for_update().filter(
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

        score_rules = event.score_rules or {1: 4, 2: 3, 3: 2, 4: 1}
        for idx, score in enumerate(scores, 1):
            score.rank = idx
            score.points = float(score_rules.get(str(idx), score_rules.get(idx, 0))) * event.score_multiplier
            score.save(update_fields=['rank', 'points'])

        return scores.count()


def calculate_team_rank_and_points(event, stage='final'):
    """重新计算某团体项目某阶段的排名和积分"""
    from django.db import transaction
    with transaction.atomic():
        scores = TeamScore.objects.select_for_update().filter(
            team_registration__event=event,
            stage=stage,
            result_numeric__isnull=False
        )

        descending_types = ['field', 'fun_individual']
        if event.event_type in descending_types and event.result_unit in ['meter', 'count']:
            scores = scores.order_by('-result_numeric')
        else:
            scores = scores.order_by('result_numeric')

        score_rules = event.score_rules or {1: 4, 2: 3, 3: 2, 4: 1}
        for idx, score in enumerate(scores, 1):
            score.rank = idx
            score.points = float(score_rules.get(str(idx), score_rules.get(idx, 0))) * event.score_multiplier
            score.save(update_fields=['rank', 'points'])

        return scores.count()


def recalculate_class_points(sports_meet):
    """重新计算班级积分（按年级单独排名 + 全校总榜）"""
    import re
    # 按年级分组: {(grade, class_name): {total, gold, silver, bronze}}
    points_map = {}

    # 个人项目积分
    for score in Score.objects.filter(
        registration__event__sports_meet=sports_meet,
        stage='final',
        points__gt=0
    ).select_related('registration__student', 'registration__event'):
        class_name = score.registration.student.class_name
        grade = _extract_grade(class_name)
        _accumulate(points_map, grade, class_name, score.points, score.rank)

    # 团体项目积分
    for team_score in TeamScore.objects.filter(
        team_registration__event__sports_meet=sports_meet,
        stage='final',
        points__gt=0
    ).select_related('team_registration'):
        class_name = team_score.team_registration.class_name
        grade = _extract_grade(class_name)
        _accumulate(points_map, grade, class_name, team_score.points, team_score.rank)

    # 清除旧积分
    ClassPoints.objects.filter(sports_meet=sports_meet).delete()

    # 每个年级单独排名
    all_grades = set(g for (g, _) in points_map.keys())
    for grade in sorted(all_grades):
        grade_data = [(cn, d) for (g, cn), d in points_map.items() if g == grade]
        grade_data.sort(key=lambda x: x[1]['total'], reverse=True)
        for rank, (class_name, data) in enumerate(grade_data, 1):
            ClassPoints.objects.create(
                sports_meet=sports_meet,
                class_name=class_name,
                grade=grade,
                total_points=round(data['total'], 1),
                gold_medals=data['gold'],
                silver_medals=data['silver'],
                bronze_medals=data['bronze'],
                rank=rank,
            )

    # 全校总榜（grade=''）
    total_map = {}
    for (grade, class_name), data in points_map.items():
        if class_name not in total_map:
            total_map[class_name] = {'total': 0, 'gold': 0, 'silver': 0, 'bronze': 0}
        for k in ['total', 'gold', 'silver', 'bronze']:
            total_map[class_name][k] += data[k]
    sorted_total = sorted(total_map.items(), key=lambda x: x[1]['total'], reverse=True)
    for rank, (class_name, data) in enumerate(sorted_total, 1):
        ClassPoints.objects.create(
            sports_meet=sports_meet,
            class_name=class_name,
            grade='',
            total_points=round(data['total'], 1),
            gold_medals=data['gold'],
            silver_medals=data['silver'],
            bronze_medals=data['bronze'],
            rank=rank,
        )


def _extract_grade(class_name):
    """从班级名提取年级，如 '2028级1班' → '2028级'"""
    import re
    m = re.match(r'(\d{4}级)', class_name)
    return m.group(1) if m else ''


def _accumulate(points_map, grade, class_name, points, rank):
    key = (grade, class_name)
    if key not in points_map:
        points_map[key] = {'total': 0, 'gold': 0, 'silver': 0, 'bronze': 0}
    points_map[key]['total'] += points
    if rank == 1:
        points_map[key]['gold'] += 1
    elif rank == 2:
        points_map[key]['silver'] += 1
    elif rank == 3:
        points_map[key]['bronze'] += 1


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
            qs = qs.filter(registration__event__referee=user,
                            registration__event__sports_meet__status='ongoing')
        elif user.role == 'teacher':
            qs = qs.filter(registration__student__class_name=user.class_name,
                            registration__event__sports_meet__status__in=['ongoing', 'finished'])
        elif user.role == 'admin':
            qs = qs.filter(registration__event__sports_meet__status__in=['ongoing', 'finished'])

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

    def _check_meet_editable(self, event):
        """检查运动会状态是否允许编辑成绩"""
        if event.sports_meet.status == 'finished':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('运动会已结束，不能修改成绩')

    def _check_referee_assignment(self, event):
        """检查裁判是否分配给此项目"""
        user = self.request.user
        if user.role == 'referee' and event.referee_id != user.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('只能操作自己负责的项目')

    def perform_create(self, serializer):
        instance = serializer.save(recorded_by=self.request.user)
        self._check_meet_editable(instance.registration.event)
        self._check_referee_assignment(instance.registration.event)

    def perform_update(self, serializer):
        instance = serializer.save()
        event = instance.registration.event
        self._check_meet_editable(event)
        self._check_referee_assignment(event)
        calculate_rank_and_points(event, instance.stage)
        recalculate_class_points(event.sports_meet)

    def perform_destroy(self, instance):
        self._check_meet_editable(instance.registration.event)
        instance.delete()

    @action(detail=False, methods=['post'], permission_classes=[IsAdminOrReferee])
    def batch_submit(self, request):
        """批量提交成绩"""
        scores_data = request.data.get('scores', [])
        if not scores_data:
            return Response({'detail': '请提供成绩数据'}, status=status.HTTP_400_BAD_REQUEST)

        # 检查第一个报名对应的事件权限
        try:
            first_reg = Registration.objects.select_related('event__sports_meet', 'event__referee').get(
                id=scores_data[0]['registration_id']
            )
        except Registration.DoesNotExist:
            return Response({'detail': '报名记录不存在'}, status=status.HTTP_404_NOT_FOUND)

        self._check_meet_editable(first_reg.event)
        self._check_referee_assignment(first_reg.event)

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

        calculate_rank_and_points(first_reg.event, scores_data[0].get('stage', 'final'))
        recalculate_class_points(first_reg.event.sports_meet)

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
        """确认晋级名单，并将晋级选手分配到下一阶段赛程"""
        event_id = request.data.get('event_id')
        advanced_registration_ids = request.data.get('registration_ids', [])
        stage = request.data.get('stage', 'preliminary')

        try:
            event = Event.objects.get(id=event_id)
        except Event.DoesNotExist:
            return Response({'detail': '项目不存在'}, status=status.HTTP_404_NOT_FOUND)

        # 确定下一阶段
        stage_order = ['preliminary', 'semifinal', 'final']
        stage_idx = stage_order.index(stage) if stage in stage_order else -1
        if stage_idx == -1 or stage_idx == len(stage_order) - 1:
            return Response({'detail': '已是最后阶段，无法晋级'}, status=status.HTTP_400_BAD_REQUEST)
        next_stage = stage_order[stage_idx + 1]

        # 获取或创建下一阶段的第一组赛程
        next_schedule, _ = Schedule.objects.get_or_create(
            event=event, stage=next_stage, group_number=1,
            defaults={'notes': '自动创建（晋级）'}
        )

        # 重置当前阶段所有成绩的晋级标记
        Score.objects.filter(
            registration__event_id=event_id, stage=stage
        ).update(is_advanced=False)

        # 标记晋级并将 registrations 分配到下一阶段赛程
        advanced_count = 0
        for idx, reg_id in enumerate(advanced_registration_ids, 1):
            Score.objects.filter(registration_id=reg_id, stage=stage).update(is_advanced=True)
            Registration.objects.filter(id=reg_id).update(schedule=next_schedule, lane=idx)
            advanced_count += 1

        return Response({
            'detail': f'已确认 {advanced_count} 人晋级 {dict(Schedule.STAGE_LABEL_CHOICES).get(next_stage, next_stage)}，已分配道次'
        })

    @action(detail=False, methods=['post'], permission_classes=[IsAdmin])
    def auto_advance_top(self, request):
        """拉通排名自动取前N晋级"""
        event_id = request.data.get('event_id')
        stage = request.data.get('stage', 'preliminary')
        advance_count = int(request.data.get('advance_count', 6))

        try:
            event = Event.objects.get(id=event_id)
        except Event.DoesNotExist:
            return Response({'detail': '项目不存在'}, status=status.HTTP_404_NOT_FOUND)

        stage_order = ['preliminary', 'semifinal', 'final']
        stage_idx = stage_order.index(stage) if stage in stage_order else -1
        if stage_idx == -1 or stage_idx == len(stage_order) - 1:
            return Response({'detail': '已是最后阶段'}, status=status.HTTP_400_BAD_REQUEST)
        next_stage = stage_order[stage_idx + 1]

        # 拉通所有组的前N名（按排名）
        top_scores = Score.objects.filter(
            registration__event_id=event_id,
            stage=stage,
            rank__isnull=False
        ).order_by('rank')[:advance_count]

        if not top_scores:
            return Response({'detail': '没有可晋级的成绩'}, status=status.HTTP_400_BAD_REQUEST)

        next_schedule, _ = Schedule.objects.get_or_create(
            event=event, stage=next_stage, group_number=1,
            defaults={'notes': '自动创建（拉通前N晋级）'}
        )

        Score.objects.filter(
            registration__event_id=event_id, stage=stage
        ).update(is_advanced=False)

        for idx, score in enumerate(top_scores, 1):
            score.is_advanced = True
            score.save(update_fields=['is_advanced'])
            Registration.objects.filter(id=score.registration_id).update(
                schedule=next_schedule, lane=idx
            )

        return Response({
            'detail': f'拉通排名自动晋级：前 {advance_count} 名已进入 {dict(Schedule.STAGE_LABEL_CHOICES).get(next_stage)}',
            'advanced': [{'name': s.registration.student.name, 'class': s.registration.student.class_name, 'rank': s.rank}
                          for s in top_scores]
        })


class TeamScoreViewSet(viewsets.ModelViewSet):
    queryset = TeamScore.objects.select_related('team_registration__event').prefetch_related('rounds').all()
    serializer_class = TeamScoreSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update']:
            return [IsAdminOrReferee()]
        if self.action == 'destroy':
            return [IsAdmin()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.role == 'referee':
            qs = qs.filter(team_registration__event__referee=user,
                            team_registration__event__sports_meet__status='ongoing')
        event_id = self.request.query_params.get('event')
        if event_id:
            qs = qs.filter(team_registration__event_id=event_id)
        return qs

    def _check_meet_editable(self, event):
        if event.sports_meet.status == 'finished':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('运动会已结束，不能修改成绩')

    def perform_create(self, serializer):
        instance = serializer.save(recorded_by=self.request.user)
        self._check_meet_editable(instance.team_registration.event)

    def perform_update(self, serializer):
        instance = serializer.save()
        event = instance.team_registration.event
        self._check_meet_editable(event)
        calculate_team_rank_and_points(event, instance.stage)
        recalculate_class_points(event.sports_meet)

    def perform_destroy(self, instance):
        self._check_meet_editable(instance.team_registration.event)
        instance.delete()


class ClassPointsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ClassPoints.objects.all()
    serializer_class = ClassPointsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        meet_id = self.request.query_params.get('sports_meet')
        if meet_id:
            qs = qs.filter(sports_meet_id=meet_id)
        grade = self.request.query_params.get('grade')
        if grade is not None:
            qs = qs.filter(grade=grade)
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
