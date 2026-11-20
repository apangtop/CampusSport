import re
from .models import SchoolProfile


def profile():
    return SchoolProfile.objects.filter(pk=1).first() or SchoolProfile(pk=1)


def class_grade(class_name, school_profile=None):
    configured = next((item['grade'] for item in (school_profile or profile()).classes if item['name'] == class_name), None)
    if configured is not None:
        return configured
    match = re.match(r'^(\d{4}级)', class_name or '')
    return match.group(1) if match else ''


def filter_class_or_grade(queryset, value, field='class_name'):
    from django.db.models import Q
    from registration.models import Student
    item = profile()
    grades = {entry['grade'] for entry in item.classes}
    known_grade = value in grades or Student.objects.filter(grade=value).exists()
    if known_grade or re.fullmatch(r'\d{4}级', value):
        names = {entry['name'] for entry in item.classes if entry['grade'] == value}
        names.update(Student.objects.filter(grade=value).values_list('class_name', flat=True))
        condition = Q(**{field + '__in': list(names)})
        if re.fullmatch(r'\d{4}级', value):
            condition |= Q(**{field + '__startswith': value})
        return queryset.filter(condition)
    return queryset.filter(**{field: value})
