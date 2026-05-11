"""
测试数据生成命令
用法: python manage.py seed_data [--clear]
"""
import random
from datetime import date, timedelta, datetime
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

# ── 班级配置 ──────────────────────────────────────────────
# 2026级=初三, 2027级=初二, 2028级=初一, 2025级=往届
GRADES = [
    ('2025级', 3),  # 往届（已毕业）
    ('2026级', 3),  # 初三
    ('2027级', 3),  # 初二
    ('2028级', 3),  # 初一
]
CLASSES_PER_GRADE = 3

MALE_NAMES = [
    '李伟', '王强', '张磊', '刘洋', '陈浩', '杨帆', '赵龙', '孙杰', '周明', '吴超',
    '郑斌', '冯涛', '蒋鹏', '韩旭', '沈宇', '唐波', '曹阳', '彭飞', '谢峰', '程远',
    '宋健', '谭辉', '江林', '贾鑫', '许诚', '何亮', '吕康', '白昊', '邓翔', '傅博',
    '薛鸿', '邵凯', '史晨', '毛炫', '覃桐', '夏宁', '戴齐', '钟逸', '梁昆', '温毅',
    '罗钧', '廖泽', '苏昊', '熊宸', '石霖', '崔恒', '雷奕', '汪杰', '魏博', '高翔',
]
FEMALE_NAMES = [
    '李娜', '王芳', '张静', '刘敏', '陈燕', '杨洁', '赵婷', '孙悦', '周丽', '吴倩',
    '郑梅', '冯雪', '蒋琳', '韩萍', '沈雨', '唐媛', '曹雅', '彭慧', '谢云', '程茜',
    '宋涵', '谭欣', '江晴', '贾莹', '许帆', '何笑', '吕蕾', '白月', '邓婵', '傅凌',
    '薛璐', '邵曼', '史珍', '毛晨', '覃晓', '夏妍', '戴瑾', '钟琳', '梁思', '温若',
    '罗悦', '廖冰', '苏宁', '熊晶', '石瑜', '崔颖', '雷晶', '汪颖', '魏佳', '高颖',
]

# ── 项目配置 ──────────────────────────────────────────────
EVENTS_TEMPLATE = [
    # (name, event_type, gender, result_unit, stage_type, max_per_class, team_size, score_multiplier)
    ('男子100米', 'track', 'male',   'second', 'two',    2, 0, 1.0),
    ('女子100米', 'track', 'female', 'second', 'two',    2, 0, 1.0),
    ('男子400米', 'track', 'male',   'second', 'single', 2, 0, 1.0),
    ('女子400米', 'track', 'female', 'second', 'single', 2, 0, 1.0),
    ('男子800米', 'track', 'male',   'second', 'single', 2, 0, 1.0),
    ('女子800米', 'track', 'female', 'second', 'single', 2, 0, 1.0),
    ('男子跳远',  'field', 'male',   'meter',  'single', 2, 0, 1.0),
    ('女子跳远',  'field', 'female', 'meter',  'single', 2, 0, 1.0),
    ('男子铅球',  'field', 'male',   'meter',  'single', 2, 0, 1.0),
    ('女子铅球',  'field', 'female', 'meter',  'single', 2, 0, 1.0),
    ('男子跳高',  'field', 'male',   'meter',  'single', 2, 0, 1.0),
    ('女子跳高',  'field', 'female', 'meter',  'single', 2, 0, 1.0),
    ('趣味呼啦圈', 'fun_individual', 'mixed', 'count', 'single', 3, 0, 1.0),
    ('趣味跳绳',  'fun_individual', 'mixed',  'count', 'single', 3, 0, 1.0),
    ('男子4×100米接力', 'relay', 'male',  'second', 'single', 1, 4, 2.0),
    ('女子4×100米接力', 'relay', 'female','second', 'single', 1, 4, 2.0),
    ('男子拔河',  'team_confrontation', 'male',  'rank', 'single', 1, 10, 2.0),
    ('女子拔河',  'team_confrontation', 'female','rank', 'single', 1, 10, 2.0),
]

SCORE_RULES = {1: 7, 2: 5, 3: 4, 4: 3, 5: 2, 6: 1}

VENUES = ['田径场直道', '田径场弯道', '跳远沙坑A', '跳远沙坑B', '铅球区', '跳高区', '操场中央', '篮球场']


def rand_result(unit, event_type):
    """生成随机成绩"""
    if unit == 'second':
        if '800' in event_type:
            v = round(random.uniform(140, 220), 2)
        elif '400' in event_type:
            v = round(random.uniform(55, 90), 2)
        elif '接力' in event_type:
            v = round(random.uniform(48, 65), 2)
        else:
            v = round(random.uniform(11.0, 16.0), 2)
        return str(v), v
    elif unit == 'meter':
        if '跳远' in event_type:
            v = round(random.uniform(3.2, 6.5), 2)
        elif '铅球' in event_type:
            v = round(random.uniform(5.0, 14.0), 2)
        else:  # 跳高
            v = round(random.uniform(1.0, 1.8), 2)
        return str(v), v
    elif unit == 'count':
        v = random.randint(30, 200)
        return str(v), float(v)
    else:
        return '', None


class Command(BaseCommand):
    help = '生成测试数据（运动会、项目、学生、报名、成绩）'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='清空所有已有数据后重新生成')

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('[!] 正在清空旧数据...')
            self._clear_data()

        self.stdout.write('── Step 1/6  创建账号 ──')
        admin, teachers, referees = self._create_users()

        self.stdout.write('── Step 2/6  创建学生 ──')
        class_students = self._create_students()  # {class_name: [Student, ...]}

        self.stdout.write('── Step 3/6  创建运动会 ──')
        meets = self._create_meets(admin)

        self.stdout.write('── Step 4/6  创建比赛项目 ──')
        events_by_meet = self._create_events(meets, referees)

        self.stdout.write('── Step 5/6  生成报名数据 ──')
        self._create_registrations(meets, events_by_meet, class_students, teachers, admin)

        self.stdout.write('── Step 6/6  录入成绩 & 汇总积分 ──')
        self._create_scores(meets, events_by_meet, admin)

        self.stdout.write(self.style.SUCCESS('\n[OK] 测试数据生成完毕！'))
        self._print_summary(meets, class_students)

    # ─────────────────────────────────────────────────────────
    def _clear_data(self):
        from scores.models import Score, TeamScore, ConfrontationRound, ClassPoints
        from registration.models import Registration, TeamRegistration, Student
        from events.models import SportsMeet, Event, Schedule
        ConfrontationRound.objects.all().delete()
        TeamScore.objects.all().delete()
        Score.objects.all().delete()
        ClassPoints.objects.all().delete()
        TeamRegistration.objects.all().delete()
        Registration.objects.all().delete()
        Schedule.objects.all().delete()
        Event.objects.all().delete()
        SportsMeet.objects.all().delete()
        Student.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        self.stdout.write('  旧数据已清空')

    # ─────────────────────────────────────────────────────────
    def _create_users(self):
        admin, _ = User.objects.get_or_create(
            username='admin',
            defaults=dict(role='admin', real_name='张体育', phone='13800000001',
                          is_staff=True, is_superuser=True)
        )
        admin.set_password('admin123')
        admin.save()

        teachers = []
        for grade_year, n_class in GRADES[1:]:  # 在校三个年级
            for cls_num in range(1, CLASSES_PER_GRADE + 1):
                class_name = f'{grade_year}{cls_num}班'
                uname = f'teacher_{grade_year}_{cls_num}'
                t, _ = User.objects.get_or_create(
                    username=uname,
                    defaults=dict(role='teacher', real_name=f'{class_name}班主任',
                                  phone=f'138{random.randint(10000000,99999999)}',
                                  class_name=class_name)
                )
                t.set_password('teacher123')
                t.save()
                teachers.append(t)

        referees = []
        for i, rname in enumerate(['王裁判', '李裁判', '陈裁判', '刘裁判'], 1):
            r, _ = User.objects.get_or_create(
                username=f'referee{i}',
                defaults=dict(role='referee', real_name=rname,
                              phone=f'139{random.randint(10000000,99999999)}')
            )
            r.set_password('referee123')
            r.save()
            referees.append(r)

        self.stdout.write(f'  管理员1 教师{len(teachers)} 裁判{len(referees)}')
        return admin, teachers, referees

    # ─────────────────────────────────────────────────────────
    def _create_students(self):
        from registration.models import Student
        class_students = {}
        sid_counter = 20240001

        for grade_year, _ in GRADES:
            for cls_num in range(1, CLASSES_PER_GRADE + 1):
                class_name = f'{grade_year}{cls_num}班'
                students = []
                male_pool = random.sample(MALE_NAMES, 15)
                female_pool = random.sample(FEMALE_NAMES, 15)
                for name in male_pool:
                    s, _ = Student.objects.get_or_create(
                        name=name, class_name=class_name,
                        defaults=dict(gender='male', student_id=str(sid_counter),
                                      grade=grade_year)
                    )
                    students.append(s)
                    sid_counter += 1
                for name in female_pool:
                    s, _ = Student.objects.get_or_create(
                        name=name, class_name=class_name,
                        defaults=dict(gender='female', student_id=str(sid_counter),
                                      grade=grade_year)
                    )
                    students.append(s)
                    sid_counter += 1
                class_students[class_name] = students

        total = sum(len(v) for v in class_students.values())
        self.stdout.write(f'  {len(class_students)}个班级，共{total}名学生')
        return class_students

    # ─────────────────────────────────────────────────────────
    def _create_meets(self, admin):
        from events.models import SportsMeet
        meets_data = [
            dict(session=1, name='第一届校园运动会', school='示范中学',
                 start_date=date(2024, 10, 15), end_date=date(2024, 10, 16),
                 registration_deadline=timezone.make_aware(datetime(2024, 10, 8, 18, 0)),
                 status='finished', max_events_per_person=3,
                 description='首届校园运动会，圆满完成'),
            dict(session=2, name='第二届校园运动会', school='示范中学',
                 start_date=date(2025, 10, 20), end_date=date(2025, 10, 21),
                 registration_deadline=timezone.make_aware(datetime(2025, 10, 13, 18, 0)),
                 status='finished', max_events_per_person=3,
                 description='第二届运动会，参与人数创历史新高'),
            dict(session=3, name='第三届校园运动会', school='示范中学',
                 start_date=date(2026, 10, 19), end_date=date(2026, 10, 20),
                 registration_deadline=timezone.make_aware(datetime(2026, 10, 12, 18, 0)),
                 status='registration', max_events_per_person=3,
                 description='第三届运动会，正在报名中'),
        ]
        meets = []
        for data in meets_data:
            m, _ = SportsMeet.objects.get_or_create(
                session=data['session'],
                defaults={**data, 'created_by': admin}
            )
            meets.append(m)
        self.stdout.write(f'  {len(meets)}届运动会')
        return meets

    # ─────────────────────────────────────────────────────────
    def _create_events(self, meets, referees):
        from events.models import Event, Schedule
        events_by_meet = {}
        for meet in meets:
            evs = []
            base_time = datetime.combine(meet.start_date, datetime.min.time()).replace(
                hour=8, minute=0, tzinfo=timezone.get_current_timezone()
            )
            time_cursor = base_time
            for tpl in EVENTS_TEMPLATE:
                name, etype, gender, unit, stage, mpc, tsize, mult = tpl
                ev, _ = Event.objects.get_or_create(
                    sports_meet=meet, name=name,
                    defaults=dict(
                        event_type=etype, gender=gender,
                        result_unit=unit, stage_type=stage,
                        max_per_class=mpc, team_size=tsize,
                        score_multiplier=mult,
                        score_rules=SCORE_RULES,
                        referee=random.choice(referees),
                        confrontation_format='bo3' if etype == 'team_confrontation' else '',
                    )
                )
                # 赛程
                stages = ['final']
                if stage == 'two':
                    stages = ['preliminary', 'final']
                elif stage == 'three':
                    stages = ['preliminary', 'semifinal', 'final']
                for si, stg in enumerate(stages):
                    Schedule.objects.get_or_create(
                        event=ev, stage=stg, group_number=1,
                        defaults=dict(
                            scheduled_time=time_cursor + timedelta(hours=si + random.randint(0, 2)),
                            venue=random.choice(VENUES),
                        )
                    )
                time_cursor += timedelta(minutes=30)
                evs.append(ev)
            events_by_meet[meet.id] = evs
            self.stdout.write(f'  {meet.name}：{len(evs)}个项目')
        return events_by_meet

    # ─────────────────────────────────────────────────────────
    def _create_registrations(self, meets, events_by_meet, class_students, teachers, admin):
        from registration.models import Registration, TeamRegistration

        all_classes = list(class_students.keys())
        in_school_classes = [c for c in all_classes if '2025级' not in c]

        for meet in meets:
            evs = events_by_meet[meet.id]
            # 每班在每个运动会中的「已用项目数」跟踪
            person_used = {}  # student_id -> count

            for ev in evs:
                is_team = ev.event_type in ('relay', 'team_confrontation')
                gender_filter = ev.gender  # male / female / mixed

                if is_team:
                    # 团体报名：每个班报一个队
                    for cls in in_school_classes:
                        students = class_students[cls]
                        if gender_filter == 'male':
                            pool = [s for s in students if s.gender == 'male']
                        elif gender_filter == 'female':
                            pool = [s for s in students if s.gender == 'female']
                        else:
                            pool = students
                        if len(pool) < ev.team_size and ev.team_size > 0:
                            continue
                        tr, _ = TeamRegistration.objects.get_or_create(
                            event=ev, class_name=cls,
                            defaults=dict(submitted_by=admin, status='approved')
                        )
                        if ev.team_size > 0:
                            members = random.sample(pool, min(ev.team_size, len(pool)))
                            tr.members.set(members)
                else:
                    # 个人报名：每班最多 max_per_class 人，且每人不超过3项
                    for cls in in_school_classes:
                        students = class_students[cls]
                        if gender_filter == 'male':
                            pool = [s for s in students if s.gender == 'male']
                        elif gender_filter == 'female':
                            pool = [s for s in students if s.gender == 'female']
                        else:
                            pool = students

                        # 按已用项目数筛选可报名学生
                        eligible = [s for s in pool
                                    if person_used.get(s.id, 0) < meet.max_events_per_person]
                        count = min(ev.max_per_class, len(eligible))
                        chosen = random.sample(eligible, count)
                        for student in chosen:
                            Registration.objects.get_or_create(
                                event=ev, student=student,
                                defaults=dict(submitted_by=admin, status='approved',
                                              lane=random.randint(1, 8))
                            )
                            person_used[student.id] = person_used.get(student.id, 0) + 1

        total_reg = sum(
            Registration.objects.filter(event__sports_meet=m).count() for m in meets
        )
        self.stdout.write(f'  共{total_reg}条个人报名记录')

    # ─────────────────────────────────────────────────────────
    def _create_scores(self, meets, events_by_meet, admin):
        from registration.models import Registration, TeamRegistration
        from scores.models import Score, TeamScore, ConfrontationRound, ClassPoints

        for meet in meets:
            if meet.status == 'registration':
                continue  # 报名中的不录成绩

            evs = events_by_meet[meet.id]
            class_points_map = {}  # class_name -> {total, gold, silver, bronze}

            for ev in evs:
                is_confrontation = ev.event_type == 'team_confrontation'
                is_team = ev.event_type in ('relay', 'team_confrontation')

                if is_team:
                    team_regs = list(TeamRegistration.objects.filter(event=ev, status='approved'))
                    if not team_regs:
                        continue

                    if is_confrontation:
                        # 拔河：随机对阵，计算胜负
                        random.shuffle(team_regs)
                        wins = {tr.class_name: 0 for tr in team_regs}
                        # 简单单循环
                        for i in range(len(team_regs)):
                            for j in range(i + 1, len(team_regs)):
                                cls_a = team_regs[i].class_name
                                cls_b = team_regs[j].class_name
                                winner = random.choice([cls_a, cls_b])
                                wins[winner] = wins.get(winner, 0) + 1

                        sorted_teams = sorted(wins.keys(), key=lambda c: -wins[c])
                        for rank, cls in enumerate(sorted_teams, 1):
                            tr = next(t for t in team_regs if t.class_name == cls)
                            ts, _ = TeamScore.objects.get_or_create(
                                team_registration=tr, stage='final',
                                defaults=dict(rank=rank, result=f'第{rank}名',
                                              points=SCORE_RULES.get(rank, 0) * ev.score_multiplier,
                                              recorded_by=admin)
                            )
                            # 胜场记录（3局）
                            for rnd in range(1, 4):
                                ConfrontationRound.objects.get_or_create(
                                    team_score=ts, round_number=rnd,
                                    defaults=dict(winner_class=cls if rank <= len(sorted_teams) // 2 else sorted_teams[-rank])
                                )
                            pts = SCORE_RULES.get(rank, 0) * ev.score_multiplier
                            _cp = class_points_map.setdefault(cls, {'total': 0, 'gold': 0, 'silver': 0, 'bronze': 0})
                            _cp['total'] += pts
                            if rank == 1: _cp['gold'] += 1
                            elif rank == 2: _cp['silver'] += 1
                            elif rank == 3: _cp['bronze'] += 1
                    else:
                        # 接力：随机排名
                        random.shuffle(team_regs)
                        for rank, tr in enumerate(team_regs, 1):
                            result_str, result_num = rand_result(ev.result_unit, ev.name)
                            pts = SCORE_RULES.get(rank, 0) * ev.score_multiplier
                            TeamScore.objects.get_or_create(
                                team_registration=tr, stage='final',
                                defaults=dict(rank=rank, result=result_str,
                                              result_numeric=result_num, points=pts,
                                              recorded_by=admin)
                            )
                            _cp = class_points_map.setdefault(tr.class_name, {'total': 0, 'gold': 0, 'silver': 0, 'bronze': 0})
                            _cp['total'] += pts
                            if rank == 1: _cp['gold'] += 1
                            elif rank == 2: _cp['silver'] += 1
                            elif rank == 3: _cp['bronze'] += 1
                else:
                    # 个人项目
                    regs = list(Registration.objects.filter(event=ev, status='approved'))
                    if not regs:
                        continue
                    # 生成成绩并排序
                    results = []
                    for reg in regs:
                        result_str, result_num = rand_result(ev.result_unit, ev.name)
                        results.append((reg, result_str, result_num))

                    # 排序：秒/米/次 asc or desc
                    reverse = ev.result_unit in ('meter', 'count')
                    results.sort(key=lambda x: x[2] if x[2] is not None else 0, reverse=reverse)

                    for rank, (reg, result_str, result_num) in enumerate(results, 1):
                        pts = SCORE_RULES.get(rank, 0) * ev.score_multiplier
                        Score.objects.get_or_create(
                            registration=reg, stage='final',
                            defaults=dict(rank=rank, result=result_str,
                                          result_numeric=result_num, points=pts,
                                          recorded_by=admin)
                        )
                        cls = reg.student.class_name
                        _cp = class_points_map.setdefault(cls, {'total': 0, 'gold': 0, 'silver': 0, 'bronze': 0})
                        _cp['total'] += pts
                        if rank == 1: _cp['gold'] += 1
                        elif rank == 2: _cp['silver'] += 1
                        elif rank == 3: _cp['bronze'] += 1

            # 写入班级积分汇总
            sorted_classes = sorted(class_points_map.keys(),
                                    key=lambda c: -class_points_map[c]['total'])
            for rank, cls in enumerate(sorted_classes, 1):
                cp = class_points_map[cls]
                ClassPoints.objects.update_or_create(
                    sports_meet=meet, class_name=cls,
                    defaults=dict(
                        total_points=round(cp['total'], 1),
                        gold_medals=cp['gold'],
                        silver_medals=cp['silver'],
                        bronze_medals=cp['bronze'],
                        rank=rank,
                    )
                )
            self.stdout.write(f'  {meet.name} 成绩录入完成，{len(sorted_classes)}个班级积分已汇总')

    # ─────────────────────────────────────────────────────────
    def _print_summary(self, meets, class_students):
        from registration.models import Registration, Student
        from scores.models import Score, ClassPoints

        self.stdout.write('\n────────── 数据概览 ──────────')
        self.stdout.write(f'  运动会：{len(meets)} 届')
        self.stdout.write(f'  班级：{len(class_students)} 个')
        self.stdout.write(f'  学生：{Student.objects.count()} 人')
        self.stdout.write(f'  报名记录：{Registration.objects.count()} 条')
        self.stdout.write(f'  成绩记录：{Score.objects.count()} 条')
        self.stdout.write(f'  班级积分记录：{ClassPoints.objects.count()} 条')

        self.stdout.write('\n  ── 历届总积分榜 Top5 ──')
        from django.db.models import Sum
        from registration.models import Student as Stu  # noqa
        from scores.models import ClassPoints as CP
        top = (CP.objects.values('class_name')
               .annotate(total=Sum('total_points'))
               .order_by('-total')[:5])
        for i, row in enumerate(top, 1):
            self.stdout.write(f'  {i}. {row["class_name"]}  {row["total"]} 分')
