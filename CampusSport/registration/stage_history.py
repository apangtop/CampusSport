from .models import Registration


def recorded_assignment(registration, stage=None):
    cache = getattr(registration,'_recorded_assignment_cache',{})
    if stage in cache: return cache[stage]
    if stage:
        from scores.models import Score, TeamScore
        model, field = (Score, 'registration') if isinstance(registration, Registration) else (TeamScore, 'team_registration')
        prefetched = getattr(registration,'_stage_scores',None)
        score = prefetched[0] if prefetched else None
        if prefetched is None:
            score = model.objects.filter(**{field:registration, 'stage':stage}).select_related('schedule').first()
        if score and score.schedule:
            result = (score.schedule,score.lane)
        elif not registration.schedule or registration.schedule.stage != stage:
            result = (None,None)
        else:
            result = (registration.schedule,registration.lane)
    else:
        result = (registration.schedule,registration.lane)
    cache[stage] = result
    registration._recorded_assignment_cache = cache
    return result


class StageScheduleMixin:
    def to_representation(self, obj):
        data = super().to_representation(obj)
        if self.context.get('stage'):
            schedule, lane = recorded_assignment(obj,self.context['stage'])
            data['schedule'],data['lane'] = getattr(schedule,'pk',None),lane
        return data

    def get_schedule_info(self, obj):
        schedule, _ = recorded_assignment(obj,self.context.get('stage'))
        if schedule:
            return {'stage':schedule.get_stage_display(), 'group_number':schedule.group_number,
                    'scheduled_time':schedule.scheduled_time,'venue':schedule.venue}
        return None


def capture_assignment(registration, stage):
    if registration.schedule and registration.schedule.stage == stage:
        return {'schedule':registration.schedule,'lane':registration.lane}
    return {'schedule':None,'lane':None}
