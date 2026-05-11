from django.db import models
from events.models import SportsMeet


class Report(models.Model):
    """生成的报告记录"""
    TYPE_CHOICES = [
        ('order_book', '秩序册'),
        ('result_report', '成绩报表'),
    ]
    FORMAT_CHOICES = [
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
    ]

    sports_meet = models.ForeignKey(SportsMeet, on_delete=models.CASCADE, related_name='reports', verbose_name='运动会')
    report_type = models.CharField('报告类型', max_length=20, choices=TYPE_CHOICES)
    file_format = models.CharField('文件格式', max_length=10, choices=FORMAT_CHOICES)
    file_path = models.CharField('文件路径', max_length=500, blank=True)
    created_at = models.DateTimeField('生成时间', auto_now_add=True)

    class Meta:
        verbose_name = '报告'
        verbose_name_plural = '报告'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.sports_meet} {self.get_report_type_display()} ({self.file_format.upper()})'
