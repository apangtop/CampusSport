from django.db import models
from django.conf import settings


class SportsMeet(models.Model):
    """运动会"""
    STATUS_CHOICES = [
        ('preparing', '筹备中'),
        ('registration', '报名中'),
        ('ongoing', '进行中'),
        ('finished', '已结束'),
    ]

    name = models.CharField('运动会名称', max_length=100)
    session = models.PositiveIntegerField('届次', default=1)
    school = models.CharField('学校名称', max_length=100, blank=True)
    start_date = models.DateField('开始日期', null=True, blank=True)
    end_date = models.DateField('结束日期', null=True, blank=True)
    registration_deadline = models.DateTimeField('报名截止时间', null=True, blank=True)
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='preparing')
    max_events_per_person = models.PositiveIntegerField('每人最多参加项目数', default=3)
    description = models.TextField('描述', blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='created_meets', verbose_name='创建人'
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '运动会'
        verbose_name_plural = '运动会'
        ordering = ['-session']

    def __str__(self):
        return f'第{self.session}届 {self.name}'


class Event(models.Model):
    """比赛项目"""
    TYPE_CHOICES = [
        ('track', '径赛'),
        ('field', '田赛'),
        ('fun_individual', '趣味个人'),
        ('team_confrontation', '对抗团体'),
        ('relay', '接力团体'),
    ]
    GENDER_CHOICES = [
        ('male', '男'),
        ('female', '女'),
        ('mixed', '混合'),
    ]
    UNIT_CHOICES = [
        ('second', '秒'),
        ('meter', '米'),
        ('count', '次'),
        ('rank', '名次'),
    ]
    STAGE_CHOICES = [
        ('single', '直接决赛'),
        ('two', '两阶段(初赛+决赛)'),
        ('three', '三阶段(初赛+半决赛+决赛)'),
    ]

    sports_meet = models.ForeignKey(SportsMeet, on_delete=models.CASCADE, related_name='events', verbose_name='运动会')
    name = models.CharField('项目名称', max_length=100)
    event_type = models.CharField('项目类型', max_length=30, choices=TYPE_CHOICES)
    gender = models.CharField('参赛性别', max_length=10, choices=GENDER_CHOICES, default='male')
    result_unit = models.CharField('成绩单位', max_length=20, choices=UNIT_CHOICES, default='second')
    stage_type = models.CharField('赛制', max_length=20, choices=STAGE_CHOICES, default='single')

    # 晋级规则（多阶段时有效）
    advance_per_group = models.PositiveIntegerField('每组晋级人数', default=2)
    advance_wildcard = models.PositiveIntegerField('通配名额', default=1)

    # 报名限制
    max_per_class = models.PositiveIntegerField('每班报名上限', default=2)
    max_per_person = models.PositiveIntegerField('每人最多参加项目数', default=3)

    # 团体项目人数
    team_size = models.PositiveIntegerField('每队人数', default=0)

    # 拔河赛制
    CONFRONTATION_FORMAT_CHOICES = [
        ('bo3', '三局两胜'),
        ('bo5', '五局三胜'),
    ]
    confrontation_format = models.CharField('对抗赛制', max_length=10, choices=CONFRONTATION_FORMAT_CHOICES, blank=True)

    # 积分规则（JSON存储: {1: 7, 2: 5, ...}）
    score_rules = models.JSONField('积分规则', default=dict, blank=True)

    # 积分倍数（团体项目）
    score_multiplier = models.FloatField('积分倍数', default=1.0)

    # 负责裁判
    referee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='responsible_events', verbose_name='负责裁判'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '比赛项目'
        verbose_name_plural = '比赛项目'
        ordering = ['sports_meet', 'event_type', 'name']

    def __str__(self):
        return f'{self.sports_meet} - {self.name}'

    def get_default_score_rules(self):
        return {1: 7, 2: 5, 3: 4, 4: 3, 5: 2, 6: 1}


class Schedule(models.Model):
    """赛程安排"""
    STAGE_LABEL_CHOICES = [
        ('preliminary', '初赛'),
        ('semifinal', '半决赛'),
        ('final', '决赛'),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='schedules', verbose_name='比赛项目')
    stage = models.CharField('阶段', max_length=20, choices=STAGE_LABEL_CHOICES, default='final')
    group_number = models.PositiveIntegerField('组次', default=1)
    scheduled_time = models.DateTimeField('比赛时间', null=True, blank=True)
    venue = models.CharField('场地', max_length=100, blank=True)
    notes = models.TextField('备注', blank=True)

    class Meta:
        verbose_name = '赛程'
        verbose_name_plural = '赛程'
        ordering = ['scheduled_time', 'group_number']

    def __str__(self):
        return f'{self.event.name} {self.get_stage_display()} 第{self.group_number}组'
