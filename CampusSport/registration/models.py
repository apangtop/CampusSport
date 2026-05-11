from django.db import models
from django.conf import settings
from events.models import Event, Schedule


class Student(models.Model):
    """学生信息"""
    GENDER_CHOICES = [('male', '男'), ('female', '女')]

    name = models.CharField('姓名', max_length=50)
    gender = models.CharField('性别', max_length=10, choices=GENDER_CHOICES)
    class_name = models.CharField('班级', max_length=50)
    student_id = models.CharField('学号', max_length=30, blank=True)
    grade = models.CharField('年级', max_length=20, blank=True)

    class Meta:
        verbose_name = '学生'
        verbose_name_plural = '学生'
        ordering = ['class_name', 'name']

    def __str__(self):
        return f'{self.class_name} {self.name}'


class Registration(models.Model):
    """报名记录"""
    STATUS_CHOICES = [
        ('submitted', '已提交'),
        ('approved', '已审核'),
        ('rejected', '已拒绝'),
        ('cancelled', '已取消'),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations', verbose_name='比赛项目')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='registrations', verbose_name='学生')
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='submitted_registrations', verbose_name='报名人'
    )
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='submitted')
    lane = models.PositiveIntegerField('道次/顺序', null=True, blank=True)
    schedule = models.ForeignKey(
        Schedule, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='participants', verbose_name='赛程'
    )
    notes = models.TextField('备注', blank=True)
    created_at = models.DateTimeField('报名时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '报名记录'
        verbose_name_plural = '报名记录'
        unique_together = [('event', 'student')]
        ordering = ['event', 'lane', 'student__class_name']

    def __str__(self):
        return f'{self.student} 报名 {self.event.name}'


class TeamRegistration(models.Model):
    """团体项目报名（接力/拔河等）"""
    STATUS_CHOICES = [
        ('submitted', '已提交'),
        ('approved', '已审核'),
        ('rejected', '已拒绝'),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='team_registrations', verbose_name='比赛项目')
    class_name = models.CharField('班级', max_length=50)
    members = models.ManyToManyField(Student, related_name='team_registrations', verbose_name='队员', blank=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='team_submitted', verbose_name='报名人'
    )
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='submitted')
    schedule = models.ForeignKey(
        Schedule, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='team_participants', verbose_name='赛程'
    )
    lane = models.PositiveIntegerField('道次/顺序', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '团体报名'
        verbose_name_plural = '团体报名'
        unique_together = [('event', 'class_name')]

    def __str__(self):
        return f'{self.class_name} 团体报名 {self.event.name}'
