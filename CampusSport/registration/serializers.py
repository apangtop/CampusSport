from rest_framework import serializers
from .models import Student, Registration, TeamRegistration
from events.models import Event


class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = '__all__'
        read_only_fields = ['id']


class RegistrationSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name', read_only=True)
    student_class = serializers.CharField(source='student.class_name', read_only=True)
    event_name = serializers.CharField(source='event.name', read_only=True)

    class Meta:
        model = Registration
        fields = '__all__'
        read_only_fields = ['id', 'submitted_by', 'created_at', 'updated_at']

    def create(self, validated_data):
        request = self.context.get('request')
        if request:
            validated_data['submitted_by'] = request.user
        return super().create(validated_data)


class RegistrationDetailSerializer(serializers.ModelSerializer):
    student = StudentSerializer(read_only=True)
    event_name = serializers.CharField(source='event.name', read_only=True)
    schedule_info = serializers.SerializerMethodField()

    class Meta:
        model = Registration
        fields = '__all__'

    def get_schedule_info(self, obj):
        if obj.schedule:
            return {
                'stage': obj.schedule.get_stage_display(),
                'group_number': obj.schedule.group_number,
                'scheduled_time': obj.schedule.scheduled_time,
                'venue': obj.schedule.venue,
            }
        return None


class TeamRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamRegistration
        fields = '__all__'
        read_only_fields = ['id', 'submitted_by', 'created_at']

    def create(self, validated_data):
        request = self.context.get('request')
        if request:
            validated_data['submitted_by'] = request.user
        members = validated_data.pop('members', [])
        team_reg = TeamRegistration.objects.create(**validated_data)
        if members:
            team_reg.members.set(members)
        return team_reg


class BulkRegistrationSerializer(serializers.Serializer):
    event_id = serializers.IntegerField()
    student_ids = serializers.ListField(child=serializers.IntegerField())
