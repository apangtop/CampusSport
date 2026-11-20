from django.db import transaction
from rest_framework import permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from CampusSport.input_validation import object_data
from .models import SchoolProfile, User
from .school import profile, class_grade
from .views import IsAdmin


class SchoolClassSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=50)
    grade = serializers.CharField(max_length=20)


class SchoolProfileSerializer(serializers.ModelSerializer):
    classes = SchoolClassSerializer(many=True, max_length=2000)

    class Meta:
        model = SchoolProfile
        fields = ['school_name', 'system_name', 'classes']

    def validate_classes(self, value):
        names = [item['name'] for item in value]
        if len(names) != len(set(names)):
            raise serializers.ValidationError('班级名称不能重复')
        from registration.models import Student
        existing = Student.objects.filter(class_name__in=names).values_list('class_name', 'grade').distinct()
        mapping = {item['name']: item['grade'] for item in value}
        for name, grade in existing:
            if grade and mapping[name] != grade:
                raise serializers.ValidationError(f'「{name}」已有学生属于「{grade}」，不能通过学校设置更改年级')
        return value


class BrandingView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        item = profile()
        return Response({'school_name': item.school_name, 'system_name': item.system_name})


class SchoolProfileView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        return Response(SchoolProfileSerializer(profile()).data)

    @transaction.atomic
    def patch(self, request):
        # get_or_create handles concurrent first writes through the singleton primary key.
        SchoolProfile.objects.get_or_create(pk=1)
        item = SchoolProfile.objects.select_for_update().get(pk=1)
        serializer = SchoolProfileSerializer(item, data=object_data(request), partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class SchoolDirectoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from registration.models import Student
        from events.models import Event
        from scores.models import ClassPoints
        item = profile()
        classes = {entry['name']: entry['grade'] for entry in item.classes}
        students = Student.objects.all()
        if request.user.role == 'teacher':
            classes = {name: grade for name, grade in classes.items() if name == request.user.class_name}
            students = students.filter(class_name=request.user.class_name)
            names = [request.user.class_name] if request.user.class_name else []
            historical = []
        else:
            names = User.objects.exclude(class_name='').values_list('class_name', flat=True).distinct()
            historical = ClassPoints.objects.values_list('class_name', 'grade').distinct()
        for name, grade in list(students.values_list('class_name', 'grade').distinct()) + list(historical):
            if name not in classes or not classes[name]:
                classes[name] = grade or class_grade(name, item)
        for name in names:
            if name not in classes:
                classes[name] = class_grade(name, item)
        grades = {grade for grade in classes.values() if grade}
        grades.update(Event.objects.exclude(grade='').values_list('grade', flat=True).distinct())
        return Response({'classes': [{'name': name, 'grade': grade} for name, grade in sorted(classes.items())],
                         'grades': sorted(grades)})
