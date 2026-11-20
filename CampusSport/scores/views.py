from CampusSport.input_validation import object_data, query_id
from rest_framework import serializers
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.db.models import Sum
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from .validation import stages
from .models import Score, TeamScore, ConfrontationRound, ClassPoints
from .serializers import ScoreSerializer, TeamScoreSerializer, ConfrontationRoundSerializer, ClassPointsSerializer
from events.models import Event, Schedule, SportsMeet
from registration.models import Registration, TeamRegistration


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
        SportsMeet.objects.select_for_update().get(pk=event.sports_meet_id)
        Score.objects.filter(registration__event=event, stage=stage).update(rank=None, points=0)
        from .workflow import eligible_individuals
        eligible = eligible_individuals(event, stage)
        scores = Score.objects.select_for_update().filter(
            registration__in=eligible,
            stage=stage,
            result_numeric__isnull=False
        )

        # 根据项目类型决定排序方向
        descending_types = ['field', 'fun_individual']
        if event.event_type == 'team_confrontation' or (event.event_type in descending_types and event.result_unit in ['meter', 'count']):
            scores = scores.order_by('-result_numeric', 'pk')
        else:
            scores = scores.order_by('result_numeric', 'pk')

        score_rules = event.score_rules or {1: 4, 2: 3, 3: 2, 4: 1}
        previous, rank = None, 0
        for idx, score in enumerate(scores, 1):
            if score.result_numeric != previous:
                rank = idx
            previous = score.result_numeric
            score.rank = rank
            score.points = (float(score_rules.get(str(rank), score_rules.get(rank, 0))) * event.score_multiplier) if stage == 'final' else 0
            score.save(update_fields=['rank', 'points'])

        return scores.count()


def calculate_team_rank_and_points(event, stage='final'):
    """重新计算某团体项目某阶段的排名和积分"""
    from django.db import transaction
    with transaction.atomic():
        SportsMeet.objects.select_for_update().get(pk=event.sports_meet_id)
        TeamScore.objects.filter(team_registration__event=event, stage=stage).update(rank=None, points=0)
        scores = TeamScore.objects.select_for_update().filter(
            team_registration__event=event,
            team_registration__status='approved',
            stage=stage,
            result_numeric__isnull=False
        )

        descending_types = ['field', 'fun_individual']
        if event.event_type == 'team_confrontation' or (event.event_type in descending_types and event.result_unit in ['meter', 'count']):
            scores = scores.order_by('-result_numeric', 'pk')
        else:
            scores = scores.order_by('result_numeric', 'pk')

        score_rules = event.score_rules or {1: 4, 2: 3, 3: 2, 4: 1}
        previous, rank = None, 0
        for idx, score in enumerate(scores, 1):
            if score.result_numeric != previous:
                rank = idx
            previous = score.result_numeric
            score.rank = rank
            score.points = (float(score_rules.get(str(rank), score_rules.get(rank, 0))) * event.score_multiplier) if stage == 'final' else 0
            score.save(update_fields=['rank', 'points'])

        return scores.count()


@transaction.atomic
def recalculate_class_points(sports_meet):
    """重新计算班级积分（按年级单独排名 + 全校总榜）"""
    from events.models import SportsMeet
    SportsMeet.objects.select_for_update().get(pk=sports_meet.pk)
    # 按年级分组: {(grade, class_name): {total, gold, silver, bronze}}
    points_map = {}

    eligible_cache = {}
    # 个人项目积分
    for score in Score.objects.filter(
        registration__event__sports_meet=sports_meet,
        stage='final',
        registration__status='approved',
        registration__event__event_type__in=['track','field','fun_individual'],
        rank__isnull=False, result_numeric__isnull=False
    ).select_related('registration__student', 'registration__event'):
        event = score.registration.event
        if event.pk not in eligible_cache:
            from .workflow import eligible_individuals
            eligible_cache[event.pk] = set(eligible_individuals(event,'final').values_list('pk',flat=True))
        if score.registration_id not in eligible_cache[event.pk]:
            continue
        class_name = score.registration.student.class_name
        grade = score.registration.student.grade or _extract_grade(class_name)
        _accumulate(points_map, grade, class_name, score.points, score.rank)

    # 团体项目积分
    for team_score in TeamScore.objects.filter(
        team_registration__event__sports_meet=sports_meet,
        stage='final',
        team_registration__status='approved',
        team_registration__event__event_type__in=['relay','team_confrontation'],
        rank__isnull=False, result_numeric__isnull=False
    ).select_related('team_registration'):
        class_name = team_score.team_registration.class_name
        member_grades = set(team_score.team_registration.members.exclude(grade='').values_list('grade', flat=True))
        grade = team_score.team_registration.event.grade or (next(iter(member_grades)) if len(member_grades) == 1 else '') or _extract_grade(class_name)
        _accumulate(points_map, grade, class_name, team_score.points, team_score.rank)

    # 清除旧积分
    ClassPoints.objects.filter(sports_meet=sports_meet).delete()

    # 每个年级单独排名
    all_grades = set(g for (g, _) in points_map.keys())
    for grade in sorted(all_grades - {''}):
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
    import math
    if not math.isfinite(points) or not math.isfinite(points_map[key]['total']+points):
        raise ValidationError('班级积分超出可计算范围，请核对计分规则')
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

        event_id = query_id(self.request.query_params, 'event')
        if event_id:
            qs = qs.filter(registration__event_id=event_id)
        stage = self.request.query_params.get('stage')
        if stage:
            qs = qs.filter(stage=stage)
        meet_id = query_id(self.request.query_params, 'sports_meet')
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
        return super().get_permissions()

    def _check_meet_editable(self, event):
        """检查运动会状态是否允许编辑成绩"""
        if event.sports_meet.status != 'ongoing':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('只有进行中的运动会允许修改成绩')

    def _check_referee_assignment(self, event):
        """检查裁判是否分配给此项目"""
        user = self.request.user
        if user.role == 'referee' and event.referee_id != user.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('只能操作自己负责的项目')

    @transaction.atomic
    def perform_create(self, serializer):
        reg = serializer.validated_data.get('registration') or serializer.validated_data.get('team_registration')
        from registration.services import lock_record
        field = 'registration' if isinstance(reg, Registration) else 'team_registration'
        serializer.validated_data[field] = lock_record(type(reg), reg.pk)
        serializer.validate(serializer.validated_data)
        instance = serializer.save(recorded_by=self.request.user)
        self._check_meet_editable(instance.registration.event)
        self._check_referee_assignment(instance.registration.event)
        calculate_rank_and_points(instance.registration.event, instance.stage)
        recalculate_class_points(instance.registration.event.sports_meet)

    @transaction.atomic
    def perform_update(self, serializer):
        reg = getattr(serializer.instance, 'registration', None) or serializer.instance.team_registration
        from registration.services import lock_record
        reg = lock_record(type(reg), reg.pk)
        serializer.instance = get_object_or_404(serializer.Meta.model.objects.select_for_update(),pk=serializer.instance.pk)
        field = 'registration' if isinstance(reg, Registration) else 'team_registration'
        setattr(serializer.instance, field, reg)
        if field in serializer.validated_data:
            serializer.validated_data[field] = reg
        serializer.validate(serializer.validated_data)
        instance = serializer.save()
        event = instance.registration.event
        self._check_meet_editable(event)
        self._check_referee_assignment(event)
        calculate_rank_and_points(event, instance.stage)
        recalculate_class_points(event.sports_meet)

    @transaction.atomic
    def perform_destroy(self, instance):
        from registration.services import lock_record
        from .workflow import protect_source_score, revoke_advancement
        reg = lock_record(Registration, instance.registration_id)
        instance = get_object_or_404(Score.objects.select_for_update(),pk=instance.pk)
        instance.registration = reg
        self._check_meet_editable(reg.event)
        protect_source_score(instance)
        revoke_advancement(instance)
        event = instance.registration.event if isinstance(instance, Score) else instance.team_registration.event
        stage = instance.stage
        instance.delete()
        if isinstance(instance, Score):
            calculate_rank_and_points(event, stage)
        else:
            calculate_team_rank_and_points(event, stage)
        recalculate_class_points(event.sports_meet)

    @action(detail=False, methods=['post'], permission_classes=[IsAdminOrReferee])
    @transaction.atomic
    def batch_submit(self, request):
        items = object_data(request).get('scores', [])
        if not isinstance(items, list) or not items or len(items) > 2000:
            raise ValidationError('请提供1到2000条成绩')
        # Validate IDs before locking in stable order to avoid partial writes and deadlocks.
        from rest_framework import serializers
        ids = serializers.ListField(child=serializers.IntegerField(min_value=1)).run_validation(
            [item.get('registration_id') if isinstance(item, dict) else None for item in items])
        meet_ids = Registration.objects.filter(pk__in=ids).values_list('event__sports_meet_id', flat=True).distinct()
        list(SportsMeet.objects.select_for_update().filter(pk__in=meet_ids).order_by('pk'))
        pending, touched, seen = [], {}, set()
        for item in items:
            if not isinstance(item, dict):
                raise ValidationError('成绩数据格式错误')
            reg_id = item.get('registration_id')
            try:
                reg = Registration.objects.select_related('event__sports_meet').get(pk=reg_id)
            except (Registration.DoesNotExist, ValueError, TypeError):
                raise ValidationError('报名记录不存在')
            stage = serializers.ChoiceField(choices=Score.STAGE_CHOICES).run_validation(item.get('stage', 'final'))
            key = (reg.pk, stage)
            if key in seen:
                raise ValidationError('批量成绩不能重复')
            seen.add(key)
            instance = Score.objects.filter(registration=reg, stage=stage).first()
            serializer = ScoreSerializer(instance, data={
                'registration': reg.pk, 'stage': stage,
                'result': item.get('result', ''), 'result_numeric': item.get('result_numeric')
            }, context={'request': request})
            serializer.is_valid(raise_exception=True)
            pending.append(serializer)
            touched[(reg.event_id, stage)] = reg.event
        for serializer in pending:
            serializer.save(recorded_by=request.user)
        meets = {}
        for (event_id, stage), event in touched.items():
            calculate_rank_and_points(event, stage)
            meets[event.sports_meet_id] = event.sports_meet
        for meet in meets.values():
            recalculate_class_points(meet)
        return Response({'results': [{'registration_id': s.instance.registration_id, 'status': 'ok'} for s in pending]})

    @action(detail=False, methods=['post'], permission_classes=[IsAdmin])
    @transaction.atomic
    def calculate_ranks(self, request):
        """手动触发排名计算"""
        event_id = serializers.IntegerField(min_value=1).run_validation(object_data(request).get('event_id'))
        stage = object_data(request).get('stage', 'final')
        try:
            event = Event.objects.get(id=event_id)
        except Event.DoesNotExist:
            return Response({'detail': '项目不存在'}, status=status.HTTP_404_NOT_FOUND)
        from registration.services import lock_event
        event = lock_event(event.pk)
        self._check_meet_editable(event)
        if stage not in stages(event):
            raise ValidationError('阶段不符合项目赛制')
        count = calculate_team_rank_and_points(event, stage) if event.event_type in ('relay', 'team_confrontation') else calculate_rank_and_points(event, stage)
        recalculate_class_points(event.sports_meet)
        return Response({'detail': f'已计算 {count} 条成绩的排名'})

    @action(detail=False, methods=['post'], permission_classes=[IsAdmin])
    @transaction.atomic
    def confirm_advancement(self, request):
        """确认晋级名单，并将晋级选手分配到下一阶段赛程"""
        event_id = serializers.IntegerField(min_value=1).run_validation(object_data(request).get('event_id'))
        advanced_registration_ids = object_data(request).get('registration_ids', [])
        stage = object_data(request).get('stage', 'preliminary')

        try:
            event = Event.objects.get(id=event_id)
        except Event.DoesNotExist:
            return Response({'detail': '项目不存在'}, status=status.HTTP_404_NOT_FOUND)

        # 确定下一阶段
        self._check_meet_editable(event)
        stage_order = stages(event)
        stage_idx = stage_order.index(stage) if stage in stage_order else -1
        if stage_idx == -1 or stage_idx == len(stage_order) - 1:
            return Response({'detail': '已是最后阶段，无法晋级'}, status=status.HTTP_400_BAD_REQUEST)
        next_stage = stage_order[stage_idx + 1]

        if not isinstance(advanced_registration_ids, list) or not advanced_registration_ids:
            raise ValidationError('请选择晋级选手')
        valid_ids = set(Score.objects.filter(registration__event=event, stage=stage,
            registration__status='approved', result_numeric__isnull=False).values_list('registration_id', flat=True))
        ids = serializers.ListField(child=serializers.IntegerField(min_value=1),max_length=2000).run_validation(advanced_registration_ids)
        if len(ids) != len(set(ids)) or not set(ids).issubset(valid_ids):
            raise ValidationError('晋级选手必须属于当前项目且有有效成绩')
        advanced_registration_ids = ids

        from registration.services import lock_event
        from .workflow import apply_advancement
        event = lock_event(event.pk)
        self._check_meet_editable(event)
        next_stage = apply_advancement(event, stage, ids)
        advanced_count = len(ids)

        return Response({
            'detail': f'已确认 {advanced_count} 人晋级 {dict(Schedule.STAGE_LABEL_CHOICES).get(next_stage, next_stage)}，已分配道次'
        })

    @action(detail=False, methods=['post'], permission_classes=[IsAdmin])
    @transaction.atomic
    def auto_advance_top(self, request):
        """拉通排名自动取前N晋级"""
        event_id = serializers.IntegerField(min_value=1).run_validation(object_data(request).get('event_id'))
        stage = object_data(request).get('stage', 'preliminary')
        advance_count = serializers.IntegerField(min_value=1,max_value=2000).run_validation(object_data(request).get('advance_count',6))

        try:
            event = Event.objects.get(id=event_id)
        except Event.DoesNotExist:
            return Response({'detail': '项目不存在'}, status=status.HTTP_404_NOT_FOUND)

        self._check_meet_editable(event)
        stage_order = stages(event)
        stage_idx = stage_order.index(stage) if stage in stage_order else -1
        if stage_idx == -1 or stage_idx == len(stage_order) - 1:
            return Response({'detail': '已是最后阶段'}, status=status.HTTP_400_BAD_REQUEST)
        next_stage = stage_order[stage_idx + 1]

        from registration.services import lock_event
        from .workflow import eligible_individuals
        event = lock_event(event.pk)
        self._check_meet_editable(event)
        calculate_rank_and_points(event, stage)
        top_scores = list(Score.objects.filter(
            registration__in=eligible_individuals(event, stage), stage=stage,
            rank__isnull=False, result_numeric__isnull=False
        ).select_related('registration__student').order_by('rank', 'pk')[:advance_count])

        if not top_scores:
            return Response({'detail': '没有可晋级的成绩'}, status=status.HTTP_400_BAD_REQUEST)

        from .workflow import apply_advancement
        next_stage = apply_advancement(event, stage, [score.registration_id for score in top_scores])

        return Response({
            'detail': f'拉通排名自动晋级：前 {len(top_scores)} 名已进入 {dict(Schedule.STAGE_LABEL_CHOICES).get(next_stage)}',
            'advanced': [{'name': s.registration.student.name, 'class': s.registration.student.class_name, 'rank': s.rank}
                          for s in top_scores]
        })


class TeamScoreViewSet(viewsets.ModelViewSet):
    queryset = TeamScore.objects.select_related('team_registration__event').prefetch_related('rounds').order_by('pk')
    serializer_class = TeamScoreSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update']:
            return [IsAdminOrReferee()]
        if self.action == 'destroy':
            return [IsAdmin()]
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.role == 'referee':
            qs = qs.filter(team_registration__event__referee=user,
                            team_registration__event__sports_meet__status='ongoing')
        if user.role == 'teacher':
            qs = qs.filter(team_registration__class_name=user.class_name, team_registration__event__sports_meet__status__in=['ongoing', 'finished'])
        meet = query_id(self.request.query_params, 'sports_meet')
        stage = self.request.query_params.get('stage')
        if meet:
            qs = qs.filter(team_registration__event__sports_meet_id=meet)
        if stage:
            qs = qs.filter(stage=stage)
        event_id = query_id(self.request.query_params, 'event')
        if event_id:
            qs = qs.filter(team_registration__event_id=event_id)
        return qs

    @action(detail=False, methods=['post'], permission_classes=[IsAdminOrReferee])
    @transaction.atomic
    def batch_submit(self, request):
        items = object_data(request).get('scores', [])
        if not isinstance(items, list) or not items or len(items) > 2000:
            raise ValidationError('请提供1到2000条团体成绩')
        ids = serializers.ListField(child=serializers.IntegerField(min_value=1)).run_validation(
            [item.get('team_registration') if isinstance(item, dict) else None for item in items])
        regs = {reg.pk: reg for reg in TeamRegistration.objects.select_related('event__sports_meet').filter(pk__in=ids)}
        if len(regs) != len(set(ids)):
            raise ValidationError('团体报名记录不存在')
        list(SportsMeet.objects.select_for_update().filter(pk__in={r.event.sports_meet_id for r in regs.values()}).order_by('pk'))
        pending, touched, seen = [], {}, set()
        for item, reg_id in zip(items, ids):
            stage = serializers.ChoiceField(choices=TeamScore.STAGE_CHOICES).run_validation(item.get('stage', 'final'))
            key = (reg_id, stage)
            if key in seen:
                raise ValidationError('批量团体成绩不能重复')
            seen.add(key)
            instance = TeamScore.objects.filter(team_registration_id=reg_id, stage=stage).first()
            serializer = TeamScoreSerializer(instance, data=item, context={'request': request})
            serializer.is_valid(raise_exception=True)
            pending.append(serializer)
            touched[(regs[reg_id].event_id, stage)] = regs[reg_id].event
        from .confrontation import validate_confrontation_batches
        validate_confrontation_batches(pending)
        for serializer in pending:
            serializer.save(recorded_by=request.user)
        meets = {}
        for (_, stage), event in touched.items():
            calculate_team_rank_and_points(event, stage)
            meets[event.sports_meet_id] = event.sports_meet
        for meet in meets.values():
            recalculate_class_points(meet)
        return Response({'results': [serializer.data for serializer in pending]})

    def _check_meet_editable(self, event):
        if event.sports_meet.status != 'ongoing':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('只有进行中的运动会允许修改成绩')

    @transaction.atomic
    def perform_create(self, serializer):
        reg = serializer.validated_data.get('registration') or serializer.validated_data.get('team_registration')
        from registration.services import lock_record
        field = 'registration' if isinstance(reg, Registration) else 'team_registration'
        serializer.validated_data[field] = lock_record(type(reg), reg.pk)
        serializer.validate(serializer.validated_data)
        instance = serializer.save(recorded_by=self.request.user)
        self._check_meet_editable(instance.team_registration.event)
        calculate_team_rank_and_points(instance.team_registration.event, instance.stage)
        recalculate_class_points(instance.team_registration.event.sports_meet)

    @transaction.atomic
    def perform_update(self, serializer):
        reg = getattr(serializer.instance, 'registration', None) or serializer.instance.team_registration
        from registration.services import lock_record
        reg = lock_record(type(reg), reg.pk)
        serializer.instance = get_object_or_404(serializer.Meta.model.objects.select_for_update(),pk=serializer.instance.pk)
        field = 'registration' if isinstance(reg, Registration) else 'team_registration'
        setattr(serializer.instance, field, reg)
        if field in serializer.validated_data:
            serializer.validated_data[field] = reg
        serializer.validate(serializer.validated_data)
        instance = serializer.save()
        event = instance.team_registration.event
        self._check_meet_editable(event)
        calculate_team_rank_and_points(event, instance.stage)
        recalculate_class_points(event.sports_meet)

    @transaction.atomic
    def perform_destroy(self, instance):
        from registration.services import lock_record
        reg = lock_record(TeamRegistration, instance.team_registration_id)
        instance = get_object_or_404(TeamScore.objects.select_for_update(),pk=instance.pk)
        instance.team_registration = reg
        self._check_meet_editable(reg.event)
        event = instance.registration.event if isinstance(instance, Score) else instance.team_registration.event
        stage = instance.stage
        instance.delete()
        if isinstance(instance, Score):
            calculate_rank_and_points(event, stage)
        else:
            calculate_team_rank_and_points(event, stage)
        recalculate_class_points(event.sports_meet)


@transaction.atomic
def rebuild_meet_results(meet):
    from registration.services import lock_event
    SportsMeet.objects.select_for_update().get(pk=meet.pk)
    for event in meet.events.order_by('pk'):
        event = lock_event(event.pk)
        if event.event_type in ('relay','team_confrontation'):
            Score.objects.filter(registration__event=event).update(rank=None,points=0)
        else:
            TeamScore.objects.filter(team_registration__event=event).update(rank=None,points=0)
        Score.objects.filter(registration__event=event).exclude(stage__in=stages(event)).update(rank=None,points=0)
        TeamScore.objects.filter(team_registration__event=event).exclude(stage__in=stages(event)).update(rank=None,points=0)
        for stage in stages(event):
            if event.event_type in ('relay','team_confrontation'):
                calculate_team_rank_and_points(event, stage)
            else:
                calculate_rank_and_points(event, stage)
    recalculate_class_points(meet)


class ClassPointsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ClassPoints.objects.all()
    serializer_class = ClassPointsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        meet_id = query_id(self.request.query_params, 'sports_meet')
        if meet_id:
            qs = qs.filter(sports_meet_id=meet_id)
        grade = self.request.query_params.get('grade')
        if grade is not None:
            qs = qs.filter(grade=grade)
        return qs.order_by('rank')

    @action(detail=False, methods=['post'], permission_classes=[IsAdmin])
    def recalculate(self, request):
        meet_id = serializers.IntegerField(min_value=1).run_validation(object_data(request).get('sports_meet_id'))
        from events.models import SportsMeet
        try:
            meet = SportsMeet.objects.get(id=meet_id)
        except SportsMeet.DoesNotExist:
            return Response({'detail': '运动会不存在'}, status=status.HTTP_404_NOT_FOUND)
        rebuild_meet_results(meet)
        return Response({'detail': '项目排名及班级积分已重新计算'})
