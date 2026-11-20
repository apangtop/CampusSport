from rest_framework import serializers
from .models import Score, TeamScore, ConfrontationRound, ClassPoints
from registration.serializers import RegistrationDetailSerializer


class ScoreValidationMixin:
    def validate(self, data):
        from .validation import validate_score
        field = 'registration' if isinstance(self, ScoreSerializer) else 'team_registration'
        registration = data.get(field, getattr(self.instance, field, None))
        stage = data.get('stage',getattr(self.instance,'stage','final'))
        if not self.instance and self.Meta.model.objects.filter(**{field:registration,'stage':stage}).exists():
            raise serializers.ValidationError('该报名本阶段已有成绩，请刷新后修改已有记录')
        if self.instance and registration.pk != getattr(self.instance, field).pk:
            raise serializers.ValidationError('不能更换成绩所属报名')
        if self.instance and data.get('stage', self.instance.stage) != self.instance.stage:
            raise serializers.ValidationError('不能更换成绩阶段')
        validate_score(registration, data.get('stage', getattr(self.instance, 'stage', 'final')),
                       data.get('result_numeric', getattr(self.instance, 'result_numeric', None)),
                       self.context['request'].user)
        if field == 'registration' and self.instance:
            changed = any(key in data and data[key] != getattr(self.instance, key) for key in ('result', 'result_numeric'))
            if changed:
                from .workflow import protect_source_score
                protect_source_score(self.instance)
        if field == 'registration' and registration.event.event_type in ('relay', 'team_confrontation'):
            raise serializers.ValidationError('团体项目不能录入个人成绩')
        if field == 'team_registration':
            from .confrontation import validate_team_result
            validate_team_result(registration, self.instance, data)
        return data


class ScoreSerializer(ScoreValidationMixin, serializers.ModelSerializer):
    def update(self, instance, validated_data):
        changed = any(key in validated_data and validated_data[key] != getattr(instance, key) for key in ('result', 'result_numeric'))
        if changed:
            from .workflow import revoke_advancement
            revoke_advancement(instance)
            instance.is_advanced = False
        return super().update(instance, validated_data)

    student_name = serializers.CharField(source='registration.student.name', read_only=True)
    class_name = serializers.CharField(source='registration.student.class_name', read_only=True)
    event_name = serializers.CharField(source='registration.event.name', read_only=True)

    class Meta:
        model = Score
        fields = '__all__'
        read_only_fields = ['id', 'recorded_by', 'recorded_at', 'updated_at', 'points', 'rank', 'is_advanced', 'schedule', 'lane']

    def create(self, validated_data):
        request = self.context.get('request')
        if request:
            validated_data['recorded_by'] = request.user
        from registration.stage_history import capture_assignment
        validated_data.update(capture_assignment(validated_data['registration'],validated_data.get('stage','final')))
        return super().create(validated_data)


class ConfrontationRoundSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfrontationRound
        fields = ['id', 'round_number', 'winner_class']


class TeamScoreSerializer(ScoreValidationMixin, serializers.ModelSerializer):
    class_name = serializers.CharField(source='team_registration.class_name', read_only=True)
    event_name = serializers.CharField(source='team_registration.event.name', read_only=True)
    rounds = ConfrontationRoundSerializer(many=True, read_only=True)
    rounds_data = ConfrontationRoundSerializer(many=True, write_only=True, required=False)

    def validate_rounds_data(self, value):
        numbers = [r['round_number'] for r in value]
        if len(numbers) != len(set(numbers)) or any(n < 1 or n > 5 for n in numbers):
            raise serializers.ValidationError('局次必须为1到5且不能重复')
        return value

    def update(self, instance, validated_data):
        rounds = validated_data.pop('rounds_data', None)
        instance = super().update(instance, validated_data)
        if rounds is not None:
            instance.rounds.all().delete()
            for rd in rounds:
                ConfrontationRound.objects.create(team_score=instance, **rd)
        return instance

    class Meta:
        model = TeamScore
        fields = '__all__'
        read_only_fields = ['id', 'recorded_by', 'recorded_at', 'updated_at', 'points', 'rank', 'is_advanced', 'schedule', 'lane']

    def create(self, validated_data):
        request = self.context.get('request')
        rounds_input = validated_data.pop('rounds_data', [])
        if request:
            validated_data['recorded_by'] = request.user
        from registration.stage_history import capture_assignment
        validated_data.update(capture_assignment(validated_data['team_registration'],validated_data.get('stage','final')))
        team_score = super().create(validated_data)
        for rd in rounds_input:
            ConfrontationRound.objects.create(
                team_score=team_score,
                round_number=rd.get('round_number', 0),
                winner_class=rd.get('winner_class', '')
            )
        return team_score


class ClassPointsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClassPoints
        fields = '__all__'
        read_only_fields = ['id', 'updated_at']
