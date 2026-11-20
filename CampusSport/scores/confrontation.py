from collections import defaultdict
from rest_framework.exceptions import ValidationError


def validate_team_result(registration, instance, data):
    event = registration.event
    if event.event_type not in ('relay', 'team_confrontation'):
        raise ValidationError('个人项目不能录入团体成绩')
    if event.event_type != 'team_confrontation':
        if data.get('rounds_data'):
            raise ValidationError('只有对抗项目可以录入局次')
        return
    if event.confrontation_format not in ('bo3','bo5'):
        raise ValidationError('项目未配置有效对抗赛制')
    needed = 3 if event.confrontation_format == 'bo5' else 2
    max_round = 2*needed-1
    supplied = 'rounds_data' in data
    rounds = data.get('rounds_data') if supplied else list(instance.rounds.values('round_number','winner_class')) if instance else []
    if any(r['round_number'] > max_round or r['winner_class'] != registration.class_name for r in rounds):
        raise ValidationError('对抗局次与队伍或赛制不匹配')
    numeric = data.get('result_numeric', getattr(instance,'result_numeric',None))
    if supplied and 'result_numeric' not in data:
        numeric = len(rounds)
        data['result_numeric'] = numeric
        if 'result' not in data:
            data['result'] = f'{numeric}胜'
    if numeric is not None and (numeric != int(numeric) or not 0 <= numeric <= needed):
        raise ValidationError(f'对抗胜局数必须为0到{needed}的整数')
    if (supplied or rounds) and numeric != len(rounds):
        raise ValidationError('胜局数必须与该队获胜局次记录一致')


def validate_confrontation_batches(serializers):
    groups = defaultdict(list)
    for serializer in serializers:
        data=serializer.validated_data
        reg=data['team_registration']
        if reg.event.event_type == 'team_confrontation':
            groups[(reg.event_id,data.get('stage',getattr(serializer.instance,'stage','final')))].append(serializer)
    for group in groups.values():
        if not any('rounds_data' in s.validated_data for s in group) or len(group)==1:
            continue
        if len(group)!=2:
            raise ValidationError('同项目阶段的局次提交须为一对队伍，当前模型不能保存多场对阵')
        winners={}
        teams=[]
        for serializer in group:
            data=serializer.validated_data
            reg=data['team_registration'];teams.append(reg.pk)
            rounds=data.get('rounds_data')
            if rounds is None:
                raise ValidationError('对阵提交须同时提供两队完整局次记录')
            for rd in rounds:
                number=rd['round_number']
                if number in winners:
                    raise ValidationError('同一局不能有两个胜者')
                winners[number]=reg.pk
        if not winners or sorted(winners)!=list(range(1,len(winners)+1)):
            raise ValidationError('比赛局次必须从1开始连续填写')
        needed=3 if group[0].validated_data['team_registration'].event.confrontation_format=='bo5' else 2
        wins={team:0 for team in teams}
        for number in sorted(winners):
            if max(wins.values())>=needed:
                raise ValidationError('比赛已经分出胜负，不能继续录入后续局次')
            wins[winners[number]]+=1
        if max(wins.values())!=needed:
            raise ValidationError('比赛尚未分出胜负')
