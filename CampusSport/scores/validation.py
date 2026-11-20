import math
from rest_framework.exceptions import PermissionDenied, ValidationError


def stages(event):
    return {'single': ['final'], 'two': ['preliminary', 'final'],
            'three': ['preliminary', 'semifinal', 'final']}[event.stage_type]


def validate_score(registration, stage, numeric, user):
    event = registration.event
    if event.sports_meet.status != 'ongoing':
        raise PermissionDenied('只有进行中的运动会允许录入成绩')
    if user.role == 'referee' and event.referee_id != user.pk:
        raise PermissionDenied('只能操作自己负责的项目')
    if registration.status != 'approved':
        raise ValidationError('只能录入已审核报名的成绩')
    if stage not in stages(event):
        raise ValidationError('成绩阶段不符合项目赛制')
    from registration.models import Registration
    if isinstance(registration, Registration):
        from .workflow import eligible_individuals
        if not eligible_individuals(event, stage).filter(pk=registration.pk).exists():
            raise ValidationError('选手未取得本阶段参赛资格，请先确认上一阶段晋级')
    if numeric is not None and (not math.isfinite(numeric) or numeric < 0):
        raise ValidationError('成绩必须为有限的非负数字')
