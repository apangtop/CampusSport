from rest_framework import serializers
from .models import SportsMeet, Event, Schedule
from accounts.serializers import UserSerializer


class ScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Schedule
        fields = '__all__'
        read_only_fields = ['id']

    def validate(self, data):
        venue = data.get('venue', getattr(self.instance, 'venue', ''))
        scheduled_time = data.get('scheduled_time', getattr(self.instance, 'scheduled_time', None))
        event = data.get('event', getattr(self.instance, 'event', None))
        from scores.validation import stages
        if data.get('stage', getattr(self.instance, 'stage', 'final')) not in stages(event):
            raise serializers.ValidationError('赛程阶段不符合项目赛制')
        if self.instance and event.pk != self.instance.event_id:
            raise serializers.ValidationError('不能更换赛程所属项目')
        if event.sports_meet.status == 'finished':
            raise serializers.ValidationError('运动会已结束，不能修改赛程')
        stage = data.get('stage', getattr(self.instance, 'stage', 'final'))
        group = data.get('group_number', getattr(self.instance, 'group_number', 1))
        if group < 1:
            raise serializers.ValidationError('组次必须为正整数')
        duplicates = Schedule.objects.filter(event=event, stage=stage, group_number=group)
        if self.instance:
            duplicates = duplicates.exclude(pk=self.instance.pk)
            from scores.models import Score, TeamScore
            if (stage != self.instance.stage or group != self.instance.group_number) and (Score.objects.filter(schedule=self.instance).exists() or TeamScore.objects.filter(schedule=self.instance).exists()):
                raise serializers.ValidationError('赛程已有历史成绩，不能更改阶段或组次')
            if stage != self.instance.stage and (self.instance.participants.exists() or self.instance.team_participants.exists()):
                raise serializers.ValidationError('赛程已有选手，不能直接更改阶段')
        if duplicates.exists():
            raise serializers.ValidationError('该项目阶段和组次已有赛程')
        if venue and scheduled_time:
            conflicts = Schedule.objects.filter(
                venue=venue,
                event__sports_meet=event.sports_meet,
                scheduled_time=scheduled_time
            ).select_related('event')
            if self.instance:
                conflicts = conflicts.exclude(id=self.instance.id)
            if conflicts.exists():
                conflict = conflicts.first()
                raise serializers.ValidationError(
                    f'时间冲突：{conflict.event.name} 已安排在「{venue}」({scheduled_time.strftime("%m/%d %H:%M")})'
                )
        return data


class EventSerializer(serializers.ModelSerializer):
    referee_info = UserSerializer(source='referee', read_only=True)
    schedules = ScheduleSerializer(many=True, read_only=True)
    registration_count = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, data):
        import math
        rules = data.get('score_rules', getattr(self.instance,'score_rules',{})) or {'1':4,'2':3,'3':2,'4':1}
        multiplier = data.get('score_multiplier',getattr(self.instance,'score_multiplier',1))
        if any(not math.isfinite(float(points)*multiplier) for points in rules.values()):
            raise serializers.ValidationError('积分规则与倍率的乘积超出可计算范围')
        if self.instance:
            event = self.instance
            has_registrations = event.registrations.exists() or event.team_registrations.exists()
            protected = {'sports_meet', 'event_type', 'gender', 'grade', 'team_size'} if has_registrations else set()
            if has_registrations or event.schedules.exists():
                protected.update({'stage_type', 'result_unit', 'sports_meet'})
            for field in protected:
                if field in data and data[field] != getattr(event, field):
                    raise serializers.ValidationError({field:'已有报名或赛程，不能直接更改比赛规则'})
            if 'confrontation_format' in data and data['confrontation_format'] != event.confrontation_format:
                from scores.models import TeamScore
                if TeamScore.objects.filter(team_registration__event=event).exists():
                    raise serializers.ValidationError('已有对抗成绩，不能更改对抗赛制')
            if event.sports_meet.status == 'finished':
                for field in ('score_rules', 'score_multiplier'):
                    if field in data and data[field] != getattr(event, field):
                        raise serializers.ValidationError('运动会已结束，不能修改计分规则')
        return data

    def update(self, instance, validated_data):
        scoring_changed = any(field in validated_data and validated_data[field] != getattr(instance, field) for field in ('score_rules','score_multiplier'))
        instance = super().update(instance, validated_data)
        if scoring_changed:
            from scores.views import calculate_rank_and_points, calculate_team_rank_and_points, recalculate_class_points
            from scores.validation import stages
            for stage in stages(instance):
                calculate_rank_and_points(instance, stage)
                calculate_team_rank_and_points(instance, stage)
            recalculate_class_points(instance.sports_meet)
        return instance

    def validate_score_rules(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError('积分规则必须是字典格式')
        normalized = {}
        for k, v in value.items():
            try:
                import math
                if isinstance(k, bool) or isinstance(v, bool) or int(k) < 1 or str(k).strip().lstrip('+').isdigit() is False or not math.isfinite(float(v)) or float(v) < 0:
                    raise ValueError
                rank = str(int(k))
                if rank in normalized:
                    raise serializers.ValidationError('同一名次不能配置重复积分规则')
                normalized[rank] = float(v)
            except (TypeError, ValueError, OverflowError):
                raise serializers.ValidationError(f'积分规则值必须为数字：{k} -> {v}')
        return normalized


    def validate_score_multiplier(self, value):
        import math
        if not math.isfinite(value) or value <= 0:
            raise serializers.ValidationError('积分倍数必须为有限正数')
        return value

    def validate_referee(self, value):
        if value and (value.role != 'referee' or not value.is_active):
            raise serializers.ValidationError('请选择启用的裁判账号')
        return value

    def get_registration_count(self, obj):
        return obj.registrations.filter(status__in=['submitted', 'approved']).count()


class EventListSerializer(serializers.ModelSerializer):
    referee_name = serializers.CharField(source='referee.real_name', read_only=True, allow_null=True)
    registration_count = serializers.SerializerMethodField()
    team_count = serializers.SerializerMethodField()
    total_max = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = ['id', 'name', 'event_type', 'gender', 'grade', 'result_unit', 'stage_type',
                  'max_per_class', 'max_per_person', 'team_size', 'referee', 'referee_name', 'confrontation_format',
                  'score_multiplier', 'registration_count', 'team_count', 'total_max']

    def get_registration_count(self, obj):
        return obj.registrations.filter(status__in=['submitted', 'approved']).count()

    def get_team_count(self, obj):
        if obj.event_type in ('relay', 'team_confrontation'):
            return obj.team_registrations.filter(status__in=['submitted', 'approved']).count()
        return 0

    def get_total_max(self, obj):
        from registration.models import Student
        base_qs = Student.objects.all()
        if obj.grade:
            base_qs = base_qs.filter(grade=obj.grade)
        class_count = base_qs.values('class_name').distinct().count() or 1
        if obj.event_type in ('relay', 'team_confrontation'):
            return class_count
        return obj.max_per_class * class_count


class SportsMeetSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.real_name', read_only=True, allow_null=True)
    event_count = serializers.SerializerMethodField()

    class Meta:
        model = SportsMeet
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']

    def get_event_count(self, obj):
        return obj.events.count()

    def validate(self, data):
        if self.instance and data.get('status') in ('preparing', 'registration'):
            from scores.models import Score, TeamScore
            if Score.objects.filter(registration__event__sports_meet=self.instance).exists() or TeamScore.objects.filter(team_registration__event__sports_meet=self.instance).exists():
                raise serializers.ValidationError('运动会已有成绩，不能退回筹备或报名阶段')
        start = data.get('start_date', getattr(self.instance, 'start_date', None))
        end = data.get('end_date', getattr(self.instance, 'end_date', None))
        if start and end and end < start:
            raise serializers.ValidationError({'end_date': '结束日期不能早于开始日期'})
        deadline = data.get('registration_deadline', getattr(self.instance, 'registration_deadline', None))
        if deadline and start and deadline.date() > start:
            raise serializers.ValidationError({'registration_deadline': '报名截止时间不能晚于开始日期'})
        return data

    def update(self, instance, validated_data):
        finishing = validated_data.get('status') == 'finished' and instance.status != 'finished'
        instance = super().update(instance, validated_data)
        if finishing:
            from scores.views import rebuild_meet_results
            rebuild_meet_results(instance)
        return instance

    def create(self, validated_data):
        from accounts.school import profile
        if not validated_data.get('school'):
            validated_data['school'] = profile().school_name
        request = self.context.get('request')
        if request and request.user:
            validated_data['created_by'] = request.user
        return super().create(validated_data)


class SportsMeetDetailSerializer(SportsMeetSerializer):
    events = EventListSerializer(many=True, read_only=True)

    class Meta(SportsMeetSerializer.Meta):
        fields = SportsMeetSerializer.Meta.fields + ['events'] if SportsMeetSerializer.Meta.fields != '__all__' else '__all__'
