from django.db import models
from django.conf import settings
from events.models import Event, Schedule
from registration.models import Registration, TeamRegistration


class Score(models.Model):
    """个人成绩"""
    STAGE_CHOICES = [
        ('preliminary', '初赛'),
        ('semifinal', '半决赛'),
        ('final', '决赛'),
    ]

    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='scores', verbose_name='报名记录')
    stage = models.CharField('阶段', max_length=20, choices=STAGE_CHOICES, default='final')
    result = models.CharField('成绩', max_length=50, blank=True)
    result_numeric = models.FloatField('数值成绩', null=True, blank=True)
    rank = models.PositiveIntegerField('名次', null=True, blank=True)
    points = models.FloatField('积分', default=0)
    is_advanced = models.BooleanField('是否晋级', default=False)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='recorded_scores', verbose_name='录入人'
    )
    recorded_at = models.DateTimeField('录入时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '成绩'
        verbose_name_plural = '成绩'
        unique_together = [('registration', 'stage')]
        ordering = ['rank']

    def __str__(self):
        return f'{self.registration.student.name} {self.get_stage_display()} {self.result}'


class TeamScore(models.Model):
    """团体成绩"""
    STAGE_CHOICES = [
        ('preliminary', '初赛'),
        ('semifinal', '半决赛'),
        ('final', '决赛'),
    ]

    team_registration = models.ForeignKey(TeamRegistration, on_delete=models.CASCADE, related_name='scores', verbose_name='团体报名')
    stage = models.CharField('阶段', max_length=20, choices=STAGE_CHOICES, default='final')
    result = models.CharField('成绩', max_length=50, blank=True)
    result_numeric = models.FloatField('数值成绩', null=True, blank=True)
    rank = models.PositiveIntegerField('名次', null=True, blank=True)
    points = models.FloatField('积分', default=0)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='recorded_team_scores', verbose_name='录入人'
    )
    recorded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '团体成绩'
        verbose_name_plural = '团体成绩'
        unique_together = [('team_registration', 'stage')]


class ConfrontationRound(models.Model):
    """拔河/对抗项目单局记录"""
    team_score = models.ForeignKey(TeamScore, on_delete=models.CASCADE, related_name='rounds', verbose_name='团体成绩')
    round_number = models.PositiveIntegerField('局次')
    winner_class = models.CharField('胜者班级', max_length=50)

    class Meta:
        verbose_name = '对抗局次'
        verbose_name_plural = '对抗局次'
        ordering = ['round_number']


class ClassPoints(models.Model):
    """班级积分汇总（按运动会+年级+班级）"""
    sports_meet = models.ForeignKey('events.SportsMeet', on_delete=models.CASCADE, related_name='class_points', verbose_name='运动会')
    class_name = models.CharField('班级', max_length=50)
    grade = models.CharField('年级', max_length=20, blank=True, help_text='留空=全校总榜')
    total_points = models.FloatField('总积分', default=0)
    gold_medals = models.PositiveIntegerField('金牌数', default=0)
    silver_medals = models.PositiveIntegerField('银牌数', default=0)
    bronze_medals = models.PositiveIntegerField('铜牌数', default=0)
    rank = models.PositiveIntegerField('排名', null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '班级积分'
        verbose_name_plural = '班级积分'
        unique_together = [('sports_meet', 'class_name', 'grade')]
        ordering = ['-total_points']

    def __str__(self):
        return f'{self.sports_meet} {self.class_name} {self.total_points}分'
