import getpass
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from accounts.models import SchoolProfile, User


class Command(BaseCommand):
    help = '初始化独立学校安装：仅创建学校配置和一个管理员，不导入演示业务数据。'

    def add_arguments(self, parser):
        parser.add_argument('--school', required=True)
        parser.add_argument('--username', required=True)
        parser.add_argument('--real-name', default='管理员')

    @transaction.atomic
    def handle(self, *args, **options):
        from registration.models import Student, Registration, TeamRegistration
        from events.models import SportsMeet
        school = options['school'].strip()
        username = options['username'].strip()
        real_name = options['real_name'].strip()
        if not school or len(school) > 100 or not username or len(username) > 150 or len(real_name) > 50:
            raise CommandError('学校、账号或姓名为空或超出长度限制')
        from django.contrib.auth.validators import UnicodeUsernameValidator
        try:
            UnicodeUsernameValidator()(username)
        except ValidationError as exc:
            raise CommandError('; '.join(exc.messages))
        # Lock singleton first, and roll back its creation if initialization is refused.
        SchoolProfile.objects.get_or_create(pk=1)
        item = SchoolProfile.objects.select_for_update().get(pk=1)
        if item.school_name or User.objects.exists() or Student.objects.exists() or SportsMeet.objects.exists() or Registration.objects.exists() or TeamRegistration.objects.exists():
            raise CommandError('安装已有学校或业务数据，初始化已拒绝；请使用学校设置和账号管理')
        password = getpass.getpass('管理员密码（至少 8 位）：')
        confirmation = getpass.getpass('再次输入密码：')
        if password != confirmation:
            raise CommandError('两次密码不一致')
        user = User(username=username, role='admin', real_name=real_name)
        try:
            validate_password(password, user=user)
        except ValidationError as exc:
            raise CommandError('; '.join(exc.messages))
        user.set_password(password)
        user.save()
        item.school_name = school
        item.save(update_fields=['school_name'])
        self.stdout.write(self.style.SUCCESS('初始化完成，请登录后配置年级和班级。'))
