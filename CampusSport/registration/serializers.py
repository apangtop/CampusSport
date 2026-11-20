from rest_framework import serializers
from .models import Student, Registration, TeamRegistration
from events.models import Event
from .stage_history import StageScheduleMixin


class StudentSerializer(serializers.ModelSerializer):
    def validate_student_id(self, value):
        return value.strip() or None if value else None

    class Meta:
        model = Student
        fields = '__all__'
        validators = []
        read_only_fields = ['id']

    def validate(self, data):
        from accounts.school import class_grade
        class_name = data.get('class_name', getattr(self.instance, 'class_name', ''))
        expected_grade = class_grade(class_name)
        if expected_grade:
            supplied = data.get('grade', getattr(self.instance, 'grade', '') if class_name == getattr(self.instance, 'class_name', '') else '')
            if supplied and supplied != expected_grade:
                raise serializers.ValidationError({'grade': '学生年级与班级所属年级不一致'})
            data['grade'] = expected_grade
        identifier = data.get('student_id',getattr(self.instance,'student_id',None))
        class_name = data.get('class_name',getattr(self.instance,'class_name',None))
        if identifier and not self.context.get('allow_identity_lookup'):
            duplicates = Student.objects.filter(class_name=class_name,student_id=identifier)
            if self.instance: duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                raise serializers.ValidationError({'student_id':'本班已有该学号的学生'})
        if not self.instance:
            return data
        student = self.instance
        class_name = data.get('class_name', student.class_name)
        gender = data.get('gender', student.gender)
        grade = data.get('grade', student.grade)
        events = [reg.event for reg in student.registrations.filter(status__in=['submitted', 'approved']).select_related('event')]
        events += [reg.event for reg in student.team_registrations.filter(status__in=['submitted', 'approved']).select_related('event')]
        if events and class_name != student.class_name:
            raise serializers.ValidationError('学生有有效报名，不能直接变更班级，请先处理报名')
        for event in events:
            if event.gender != 'mixed' and gender != event.gender:
                raise serializers.ValidationError('性别变更会使已有报名不符合项目要求')
            if event.grade and grade != event.grade:
                raise serializers.ValidationError('年级变更会使已有报名不符合项目要求')
        return data


class RegistrationSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name', read_only=True)
    student_class = serializers.CharField(source='student.class_name', read_only=True)
    student_gender = serializers.CharField(source='student.gender', read_only=True)
    event_name = serializers.CharField(source='event.name', read_only=True)

    class Meta:
        model = Registration
        fields = '__all__'
        validators = []
        read_only_fields = ['id', 'submitted_by', 'created_at', 'updated_at', 'status']

    def validate(self, data):
        from .validation import validate_individual, validate_assignment, assignment_only, check_registration_open
        user = self.context['request'].user
        event = data.get('event', getattr(self.instance, 'event', None))
        student = data.get('student', getattr(self.instance, 'student', None))
        if self.instance and (event.pk != self.instance.event_id or student.pk != self.instance.student_id):
            raise serializers.ValidationError('不能更换报名所属项目或学生，请重新报名')
        validate_assignment(event, self.instance, data, user)
        if assignment_only(data, self.instance, user):
            return data
        existing = self.instance or Registration.objects.filter(event=event, student=student).first()
        if self.instance and self.instance.status in ('cancelled', 'rejected') and self.context['request'].method in ('PUT', 'PATCH'):
            check_registration_open(event, user)
        else:
            validate_individual(event, student, user, existing)
        return data

    def create(self, validated_data):
        request = self.context.get('request')
        if request:
            validated_data['submitted_by'] = request.user
        return super().create(validated_data)


class RegistrationDetailSerializer(StageScheduleMixin, serializers.ModelSerializer):
    student = StudentSerializer(read_only=True)
    event_name = serializers.CharField(source='event.name', read_only=True)
    schedule_info = serializers.SerializerMethodField()

    class Meta:
        model = Registration
        fields = '__all__'


class TeamRegistrationSerializer(StageScheduleMixin, serializers.ModelSerializer):
    schedule_info = serializers.SerializerMethodField()

    members_detail = StudentSerializer(source='members', many=True, read_only=True)

    class Meta:
        model = TeamRegistration
        fields = '__all__'
        validators = []
        read_only_fields = ['id', 'submitted_by', 'created_at', 'status']

    def create(self, validated_data):
        request = self.context.get('request')
        if request:
            validated_data['submitted_by'] = request.user
        members = validated_data.pop('members', [])
        team_reg = TeamRegistration.objects.create(**validated_data)
        if members:
            team_reg.members.set(members)
        return team_reg

    def validate(self, data):
        from .validation import validate_team, validate_assignment, assignment_only
        event = data.get('event', getattr(self.instance, 'event', None))
        user = self.context['request'].user
        if self.instance and event.pk != self.instance.event_id:
            raise serializers.ValidationError('不能更换团体报名所属项目')
        class_name = data.get('class_name', getattr(self.instance, 'class_name', ''))
        if self.instance and class_name != self.instance.class_name:
            raise serializers.ValidationError('不能更换团体报名所属班级')
        validate_assignment(event, self.instance, data, user)
        if assignment_only(data, self.instance, user):
            return data
        members = data.get('members', list(self.instance.members.all()) if self.instance else [])
        validate_team(event, class_name, members, user)
        return data

    def update(self, instance, validated_data):
        if 'members' in validated_data:
            old = set(instance.members.values_list('pk', flat=True))
            new = {member.pk for member in validated_data['members']}
            if old != new:
                validated_data.update(status='submitted', schedule=None, lane=None)
        return super().update(instance, validated_data)


class BulkRegistrationSerializer(serializers.Serializer):
    event_id = serializers.IntegerField(min_value=1)
    student_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), min_length=1, max_length=50)


    def validate_student_ids(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError('学生ID不能重复')
        return value
