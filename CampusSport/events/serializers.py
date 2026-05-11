from rest_framework import serializers
from .models import SportsMeet, Event, Schedule
from accounts.serializers import UserSerializer


class ScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Schedule
        fields = '__all__'
        read_only_fields = ['id']

    def validate(self, data):
        venue = data.get('venue', '')
        scheduled_time = data.get('scheduled_time')
        event = data.get('event')
        if venue and scheduled_time:
            conflicts = Schedule.objects.filter(
                venue=venue,
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

    def validate_score_rules(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError('积分规则必须是字典格式')
        for k, v in value.items():
            try:
                float(v)
            except (TypeError, ValueError):
                raise serializers.ValidationError(f'积分规则值必须为数字：{k} -> {v}')
        return value

    def get_registration_count(self, obj):
        return obj.registrations.filter(status__in=['submitted', 'approved']).count()


class EventListSerializer(serializers.ModelSerializer):
    referee_name = serializers.CharField(source='referee.real_name', read_only=True, allow_null=True)
    registration_count = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = ['id', 'name', 'event_type', 'gender', 'result_unit', 'stage_type',
                  'max_per_class', 'referee', 'referee_name',
                  'score_multiplier', 'registration_count']

    def get_registration_count(self, obj):
        return obj.registrations.filter(status__in=['submitted', 'approved']).count()


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
        start = data.get('start_date')
        end = data.get('end_date')
        if start and end and end < start:
            raise serializers.ValidationError({'end_date': '结束日期不能早于开始日期'})
        deadline = data.get('registration_deadline')
        if deadline and start and deadline.date() > start:
            raise serializers.ValidationError({'registration_deadline': '报名截止时间不能晚于开始日期'})
        return data

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user:
            validated_data['created_by'] = request.user
        return super().create(validated_data)


class SportsMeetDetailSerializer(SportsMeetSerializer):
    events = EventListSerializer(many=True, read_only=True)

    class Meta(SportsMeetSerializer.Meta):
        fields = SportsMeetSerializer.Meta.fields + ['events'] if SportsMeetSerializer.Meta.fields != '__all__' else '__all__'
