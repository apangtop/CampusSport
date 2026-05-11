from rest_framework import serializers
from .models import Score, TeamScore, ConfrontationRound, ClassPoints
from registration.serializers import RegistrationDetailSerializer


class ScoreSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='registration.student.name', read_only=True)
    class_name = serializers.CharField(source='registration.student.class_name', read_only=True)
    event_name = serializers.CharField(source='registration.event.name', read_only=True)

    class Meta:
        model = Score
        fields = '__all__'
        read_only_fields = ['id', 'recorded_by', 'recorded_at', 'updated_at', 'points', 'rank']

    def create(self, validated_data):
        request = self.context.get('request')
        if request:
            validated_data['recorded_by'] = request.user
        return super().create(validated_data)


class ConfrontationRoundSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfrontationRound
        fields = ['id', 'round_number', 'winner_class']


class TeamScoreSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source='team_registration.class_name', read_only=True)
    rounds = ConfrontationRoundSerializer(many=True, read_only=True)
    rounds_data = serializers.ListField(child=serializers.DictField(), write_only=True, required=False)

    class Meta:
        model = TeamScore
        fields = '__all__'
        read_only_fields = ['id', 'recorded_by', 'recorded_at', 'updated_at', 'points', 'rank']

    def create(self, validated_data):
        request = self.context.get('request')
        rounds_input = validated_data.pop('rounds_data', [])
        if request:
            validated_data['recorded_by'] = request.user
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
