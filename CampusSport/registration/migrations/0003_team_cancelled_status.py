from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('registration', '0002_auto_20260511_1403')]
    operations = [
        migrations.AlterField(model_name='teamregistration', name='status',
            field=models.CharField(choices=[('cancelled', '已取消'), ('submitted', '已提交'),
                ('approved', '已审核'), ('rejected', '已拒绝')], default='submitted', max_length=20, verbose_name='状态')),
        migrations.AlterModelOptions(name='teamregistration', options={
            'verbose_name': '团体报名', 'verbose_name_plural': '团体报名', 'ordering': ['event_id', 'pk']}),
    ]
