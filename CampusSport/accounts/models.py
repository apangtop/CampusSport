from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', '体育老师'),
        ('teacher', '班主任'),
        ('referee', '裁判'),
    ]

    role = models.CharField('角色', max_length=20, choices=ROLE_CHOICES, default='teacher')
    real_name = models.CharField('真实姓名', max_length=50, blank=True)
    phone = models.CharField('手机号', max_length=20, blank=True)
    # 班主任绑定的班级名称
    class_name = models.CharField('班级', max_length=50, blank=True)

    class Meta:
        verbose_name = '用户'
        verbose_name_plural = '用户'

    def __str__(self):
        return f'{self.real_name or self.username}({self.get_role_display()})'
