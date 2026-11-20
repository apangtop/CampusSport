from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from .models import Registration

ACTIVE_STATUSES = ('submitted', 'approved')
TEAM_TYPES = ('relay', 'team_confrontation')


def check_meet_open(meet, user):
    if meet.status in ('ongoing', 'finished'):
        raise ValidationError('进行中或已结束的运动会不能修改报名')
    if user.role != 'admin':
        if meet.status != 'registration':
            raise ValidationError('当前不在报名阶段')
        if meet.registration_deadline and timezone.now() >= meet.registration_deadline:
            raise ValidationError('报名已截止')


def check_registration_open(event, user):
    check_meet_open(event.sports_meet, user)


def validate_student(event, student, user):
    if user.role == 'teacher' and student.class_name != user.class_name:
        raise PermissionDenied('只能为本班学生报名')
    if event.gender != 'mixed' and student.gender != event.gender:
        raise ValidationError('学生性别不符合项目要求')
    if event.grade and student.grade != event.grade:
        raise ValidationError('学生年级不符合项目要求')


def validate_individual(event, student, user, instance=None):
    check_registration_open(event, user)
    if event.event_type in TEAM_TYPES:
        raise ValidationError('团体项目请使用团体报名')
    validate_student(event, student, user)
    active = Registration.objects.filter(status__in=ACTIVE_STATUSES)
    if instance:
        active = active.exclude(pk=instance.pk)
    if active.filter(event=event, student__class_name=student.class_name).count() >= event.max_per_class:
        raise ValidationError(f'已达到每班报名上限（{event.max_per_class}人）')
    # 团体队员不占个人项目名额。
    cap = min(event.max_per_person or event.sports_meet.max_events_per_person,
              event.sports_meet.max_events_per_person)
    if active.filter(student=student, event__sports_meet=event.sports_meet,
                     event__event_type__in=['track', 'field', 'fun_individual']).count() >= cap:
        raise ValidationError(f'已达到每人报名项目上限（{cap}项）')


def validate_team(event, class_name, members, user):
    check_registration_open(event, user)
    if event.event_type not in TEAM_TYPES:
        raise ValidationError('个人项目请使用个人报名')
    if not class_name or (user.role == 'teacher' and class_name != user.class_name):
        raise PermissionDenied('只能为本班报名团体项目')
    if event.team_size <= 0:
        raise ValidationError('项目尚未配置有效的每队人数，请联系体育老师')
    if len({member.pk for member in members}) != len(members):
        raise ValidationError('队员不能重复')
    if len(members) != event.team_size:
        raise ValidationError(f'需要 {event.team_size} 名队员，当前选择了 {len(members)} 名')
    for member in members:
        if member.class_name != class_name:
            raise ValidationError('所有队员必须属于报名班级')
        validate_student(event, member, user)


def validate_assignment(event, instance, data, user):
    if user.role != 'admin' and any(key in data for key in ('schedule', 'lane')):
        raise PermissionDenied('只有体育老师可以调整赛程和道次')
    schedule = data.get('schedule', getattr(instance, 'schedule', None))
    lane = data.get('lane', getattr(instance, 'lane', None))
    if schedule and schedule.event_id != event.pk:
        raise ValidationError('赛程与比赛项目不匹配')
    if lane is not None and lane < 1:
        raise ValidationError('道次或序号必须为正整数')
    changed = instance and any(key in data and data[key] != getattr(instance,key) for key in ('schedule','lane'))
    if changed:
        from .models import TeamRegistration
        from scores.models import Score, TeamScore
        score_model, field = (TeamScore,'team_registration') if isinstance(instance,TeamRegistration) else (Score,'registration')
        old_schedule = getattr(instance,'schedule',None)
        affected_stages = {schedule.stage} if schedule else set()
        if old_schedule and (not schedule or schedule.stage == old_schedule.stage):
            affected_stages.add(old_schedule.stage)
        if score_model.objects.filter(**{field:instance,'stage__in':affected_stages}).exists():
            raise ValidationError('相关阶段已有成绩，不能更改已记录的赛程和道次')
    if any(key in data and data[key] is not None for key in ('schedule', 'lane')):
        if not instance or instance.status != 'approved':
            raise ValidationError('只有已审核报名可以分配赛程和道次')
        if schedule and lane is not None:
            from .models import TeamRegistration
            model = TeamRegistration if isinstance(instance, TeamRegistration) else Registration
            if model.objects.filter(schedule=schedule, lane=lane, status='approved').exclude(pk=instance.pk).exists():
                raise ValidationError('该赛程的道次或序号已被占用')
    if instance and instance.status not in ACTIVE_STATUSES and (schedule or lane):
        # An inactive record can carry old assignments; only reject new assignment attempts.
        if any(key in data and data[key] is not None for key in ('schedule', 'lane')):
            raise ValidationError('取消或拒绝的报名不能分配赛程和道次')


def assignment_only(data, instance, user):
    if not instance or not data or not set(data).issubset({'schedule', 'lane', 'notes'}):
        return False
    if user.role == 'admin':
        if instance.event.sports_meet.status == 'finished':
            raise ValidationError('运动会已结束，不能调整报名')
        return True
    return False
