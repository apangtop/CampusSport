from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.exceptions import ValidationError, PermissionDenied
from events.models import Event, SportsMeet
from .models import Registration, TeamRegistration, Student
from .validation import (ACTIVE_STATUSES, check_meet_open, check_registration_open,
                         validate_individual, validate_team)


def lock_event(event_id):
    initial = get_object_or_404(Event, pk=event_id)
    meet = get_object_or_404(SportsMeet.objects.select_for_update(), pk=initial.sports_meet_id)
    event = get_object_or_404(Event.objects.select_for_update(), pk=event_id)
    if event.sports_meet_id != meet.pk:
        raise ValidationError('项目所属运动会已变化，请刷新重试')
    event.sports_meet = meet
    return event


def lock_record(model, pk):
    initial = get_object_or_404(model, pk=pk)
    event = lock_event(initial.event_id)
    record = get_object_or_404(model.objects.select_for_update(), pk=pk)
    record.event = event
    if model is Registration:
        record.student = get_object_or_404(Student.objects.select_for_update(), pk=record.student_id)
    return record


def validate_record(record, user):
    if isinstance(record, Registration):
        validate_individual(record.event, record.student, user, record)
    else:
        validate_team(record.event, record.class_name, list(record.members.all()), user)


@transaction.atomic
def submit(serializer, user):
    data = serializer.validated_data
    event = lock_event(data['event'].pk)
    data['event'] = event
    model = serializer.Meta.model
    if model is Registration:
        data['student'] = get_object_or_404(Student.objects.select_for_update(), pk=data['student'].pk)
    else:
        members = data.get('members', [])
        data['members'] = list(Student.objects.select_for_update().filter(pk__in=[m.pk for m in members]).order_by('pk'))
        if len(data['members']) != len(members):
            raise ValidationError('队员数据已变化，请刷新重试')
    lookup = {'event': event, 'student': data['student']} if model is Registration else {'event': event, 'class_name': data['class_name']}
    existing = model.objects.select_for_update().filter(**lookup).first()
    if existing and existing.status in ACTIVE_STATUSES:
        raise ValidationError('已经报名本项目，请勿重复提交')
    serializer.instance = existing
    serializer.validate(data)
    if existing:
        existing.event = event
        serializer.save(submitted_by=user, status='submitted', schedule=None, lane=None)
    else:
        serializer.save(submitted_by=user, status='submitted')


@transaction.atomic
def change_status(model, pk, status, user):
    record = lock_record(model, pk)
    if model is TeamRegistration:
        list(Student.objects.select_for_update().filter(team_registrations=record).order_by('pk'))
    check_registration_open(record.event, user)
    if status == 'cancelled':
        if record.status == 'cancelled':
            return record
        if record.status not in ACTIVE_STATUSES:
            raise ValidationError('只能取消待审核或已审核报名')
    elif record.status != 'submitted':
        raise ValidationError('只能审核或拒绝待审核报名')
    if status == 'approved':
        validate_record(record, user)
    record.status = status
    if status in ('cancelled', 'rejected'):
        record.schedule = None
        record.lane = None
    record.save()
    return record


@transaction.atomic
def approve_batch(model, payload, user):
    if not isinstance(payload, dict):
        raise ValidationError('审核参数必须为对象')
    event_id = payload.get('event_id')
    meet_id = payload.get('sports_meet_id')
    field = serializers.IntegerField(min_value=1)
    if event_id is None and meet_id is None:
        raise ValidationError('请指定运动会或比赛项目，禁止无范围审核')
    event_id = field.run_validation(event_id) if event_id is not None else None
    meet_id = field.run_validation(meet_id) if meet_id is not None else None
    if event_id:
        event = get_object_or_404(Event, pk=event_id)
        if meet_id and event.sports_meet_id != meet_id:
            raise ValidationError('比赛项目不属于指定运动会')
        meet_id = event.sports_meet_id
    meet = get_object_or_404(SportsMeet.objects.select_for_update(), pk=meet_id)
    check_meet_open(meet, user)
    qs = model.objects.filter(event__sports_meet=meet, status='submitted')
    if event_id:
        qs = qs.filter(event_id=event_id)
    class_name = payload.get('class_name')
    if class_name is not None:
        class_name = serializers.CharField(max_length=50).run_validation(class_name)
        key = 'student__class_name' if model is Registration else 'class_name'
        key += '__startswith' if class_name.endswith('级') else ''
        qs = qs.filter(**{key: class_name})
    event_type = payload.get('type')
    if event_type is not None:
        event_type = serializers.ChoiceField(choices=Event.TYPE_CHOICES).run_validation(event_type)
        qs = qs.filter(event__event_type=event_type)
    # Lock student rows in stable order before reading any eligibility data.
    if model is Registration:
        ids = qs.values_list('student_id', flat=True)
    else:
        ids = qs.values_list('members__pk', flat=True)
    list(Student.objects.select_for_update().filter(pk__in=ids).order_by('pk'))
    approved, errors = 0, []
    for record in qs.select_related('event', 'student' if model is Registration else 'submitted_by').order_by('pk'):
        record.event.sports_meet = meet
        try:
            validate_record(record, user)
        except (ValidationError, PermissionDenied) as exc:
            errors.append({'id': record.pk, 'detail': exc.detail})
            continue
        record.status = 'approved'
        record.save(update_fields=['status'])
        approved += 1
    return {'approved': approved, 'errors': errors, 'detail': f'已审核 {approved} 条报名，{len(errors)} 条未通过校验'}



@transaction.atomic
def import_student(lookup, values, request):
    from .serializers import StudentSerializer
    matches = list(Student.objects.select_for_update().filter(**lookup).order_by('pk')[:2])
    if len(matches) > 1:
        raise ValidationError('存在多条同学号或同姓名记录，请先核对学生数据')
    instance = matches[0] if matches else None
    serializer = StudentSerializer(instance, data={**lookup, **values}, partial=bool(instance), context={'request': request})
    serializer.is_valid(raise_exception=True)
    from django.db import IntegrityError
    try:
        with transaction.atomic():
            return serializer.save(), instance is None
    except IntegrityError:
        raise ValidationError('学生学号已存在，请核对或刷新后重试')


@transaction.atomic
def create_student_once(data, request):
    from .serializers import StudentSerializer
    serializer = StudentSerializer(data=data, context={'request':request,'allow_identity_lookup':True})
    serializer.is_valid(raise_exception=True)
    values=serializer.validated_data
    if request.user.role == 'teacher' and values['class_name'] != request.user.class_name:
        raise PermissionDenied('只能添加本班学生')
    lookup={'class_name':values['class_name']}
    lookup['student_id' if values.get('student_id') else 'name']=values.get('student_id') or values['name']
    matches=list(Student.objects.select_for_update().filter(**lookup).order_by('pk')[:2])
    if len(matches)>1:
        raise ValidationError('存在多条同名或同学号记录，请提供明确学号并先核对数据')
    if matches:
        instance=matches[0]
        if any(value != getattr(instance,key) for key,value in values.items()):
            raise ValidationError('已存在学生的资料与请求不一致，请使用编辑或导入功能核对更新')
        return instance, False
    from django.db import IntegrityError
    try:
        with transaction.atomic():
            return serializer.save(), True
    except IntegrityError:
        raise ValidationError('学生身份已被其他请求创建，请刷新后重试')
