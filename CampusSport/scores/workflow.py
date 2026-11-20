from django.db import transaction
from rest_framework.exceptions import ValidationError
from registration.models import Registration
from .models import Score
from .validation import stages


def eligible_individuals(event, stage):
    order = stages(event)
    if stage not in order:
        raise ValidationError('阶段不符合项目赛制')
    qs = Registration.objects.filter(event=event, status='approved')
    index = order.index(stage)
    for previous_stage in order[:index]:
        qs = qs.filter(scores__stage=previous_stage, scores__is_advanced=True,
                       scores__result_numeric__isnull=False)
    return qs.distinct()


def protect_source_score(score):
    later = stages(score.registration.event)[stages(score.registration.event).index(score.stage)+1:]
    if later and Score.objects.filter(registration=score.registration, stage__in=later).exists():
        raise ValidationError('后续阶段已有成绩，请先处理后续成绩，再修改或删除晋级来源成绩')


def revoke_advancement(score):
    order = stages(score.registration.event)
    later = order[order.index(score.stage)+1:]
    if later:
        Score.objects.filter(pk=score.pk).update(is_advanced=False)
        Registration.objects.filter(pk=score.registration_id, schedule__stage__in=later).update(schedule=None, lane=None)


@transaction.atomic
def apply_advancement(event, stage, ids):
    if event.event_type in ('relay', 'team_confrontation'):
        raise ValidationError('此晋级接口仅支持个人项目')
    order = stages(event)
    if stage not in order or stage == order[-1]:
        raise ValidationError('当前阶段不能晋级')
    next_stage = order[order.index(stage)+1]
    source = Score.objects.filter(registration__in=eligible_individuals(event, stage),
                                  stage=stage, result_numeric__isnull=False)
    valid_ids = set(source.values_list('registration_id', flat=True))
    if not ids or len(ids) != len(set(ids)) or not set(ids).issubset(valid_ids):
        raise ValidationError('晋级选手必须属于当前项目且有有效成绩和参赛资格')
    selected = set(ids)
    later = order[order.index(stage)+1:]
    # Any downstream score prevents revoking eligibility; same selection is idempotent.
    if Score.objects.filter(registration__event=event, stage__in=later).exclude(registration_id__in=selected).exists():
        raise ValidationError('落选选手已有后续阶段成绩，请先处理后续成绩')
    from events.models import Schedule
    old = set(source.filter(is_advanced=True).values_list('registration_id', flat=True))
    if old == selected:
        return next_stage
    Registration.objects.filter(event=event, schedule__stage__in=later).exclude(pk__in=selected).update(schedule=None, lane=None)
    Score.objects.filter(registration__event=event, stage=stage).update(is_advanced=False)
    source.filter(registration_id__in=selected).update(is_advanced=True)
    schedule, _ = Schedule.objects.get_or_create(event=event, stage=next_stage, group_number=1,
                                                 defaults={'notes':'自动创建（晋级）'})
    occupied = set(Registration.objects.filter(schedule=schedule, status='approved', lane__isnull=False)
                   .exclude(pk__in=selected-old).values_list('lane',flat=True))
    lane = 1
    for reg in Registration.objects.filter(pk__in=ids).select_related('schedule').order_by('pk'):
        if reg.pk in old and reg.schedule and reg.schedule.stage in later:
            continue
        while lane in occupied:
            lane += 1
        reg.schedule, reg.lane = schedule, lane
        reg.save(update_fields=['schedule','lane'])
        occupied.add(lane)
    return next_stage
