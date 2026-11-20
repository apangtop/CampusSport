import io
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from rest_framework.test import APIClient
from accounts.models import User, SchoolProfile
from events.models import SportsMeet, Event
from registration.models import Student, Registration, TeamRegistration
from scores.models import ClassPoints


class SchoolDeliveryTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user('school-admin', role='admin')
        self.teacher = User.objects.create_user('school-teacher', role='teacher', class_name='高一1班')
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        self.classes = [{'name': '高一1班', 'grade': '高一'}, {'name': '一年级1班', 'grade': '小学一年级'}]

    def configure(self):
        response = self.client.patch('/api/school/profile/', {'school_name': '测试学校', 'system_name': '校运管理', 'classes': self.classes}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        return response

    def test_public_branding_works_with_expired_jwt_and_excludes_directory(self):
        self.configure()
        anonymous = APIClient(); anonymous.credentials(HTTP_AUTHORIZATION='Bearer invalid-token')
        response = anonymous.get('/api/school/branding/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'school_name': '测试学校', 'system_name': '校运管理'})

    def test_read_default_profile_does_not_write_database(self):
        self.assertEqual(self.client.get('/api/school/profile/').status_code, 200)
        self.assertFalse(SchoolProfile.objects.exists())

    def test_anonymous_cannot_read_profile_or_directory(self):
        client = APIClient()
        for url in ['/api/school/profile/', '/api/school/directory/']:
            self.assertEqual(client.get(url).status_code, 401)

    def test_teacher_cannot_change_school(self):
        self.client.force_authenticate(self.teacher)
        self.assertEqual(self.client.patch('/api/school/profile/', {'school_name': '其他'}, format='json').status_code, 403)
        self.assertFalse(SchoolProfile.objects.exists())

    def test_invalid_profile_updates_are_atomic(self):
        self.configure()
        for classes in [[{'name': '重复', 'grade': '一年级'}] * 2, [{'name': '甲', 'grade': ''}], [{'name': '甲' * 51, 'grade': '一年级'}]]:
            response = self.client.patch('/api/school/profile/', {'school_name': '不应保存', 'classes': classes}, format='json')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(SchoolProfile.objects.get().school_name, '测试学校')

    def test_profile_rejects_array_payload(self):
        response = self.client.patch('/api/school/profile/', [], format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(SchoolProfile.objects.exists())

    def test_profile_singleton_has_database_constraint(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            SchoolProfile.objects.create(pk=2)

    def test_directory_preserves_existing_students_and_historical_rankings(self):
        self.configure()
        Student.objects.create(name='旧生', gender='male', class_name='历史班', grade='历史年级')
        meet = SportsMeet.objects.create(name='往届')
        ClassPoints.objects.create(sports_meet=meet, class_name='往届班', grade='往届年级')
        response = self.client.get('/api/school/directory/')
        self.assertIn({'name': '历史班', 'grade': '历史年级'}, response.data['classes'])
        self.assertIn('往届年级', response.data['grades'])

    def test_teacher_directory_only_contains_own_class(self):
        self.configure()
        Student.objects.create(name='其他', gender='male', class_name='其他班', grade='其他年级')
        self.client.force_authenticate(self.teacher)
        response = self.client.get('/api/school/directory/')
        self.assertEqual(response.data['classes'], [self.classes[0]])

    def test_profile_cannot_reassign_grade_of_existing_students(self):
        self.configure()
        Student.objects.create(name='甲', gender='male', class_name='高一1班', grade='高一')
        response = self.client.patch('/api/school/profile/', {'classes': [{'name': '高一1班', 'grade': '高二'}]}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(SchoolProfile.objects.get().classes, self.classes)

    def test_student_grade_is_inferred_for_custom_class(self):
        self.configure()
        response = self.client.post('/api/students/', {'name': '甲', 'gender': 'male', 'class_name': '高一1班'}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['grade'], '高一')

    def test_student_wrong_grade_is_rejected(self):
        self.configure()
        response = self.client.post('/api/students/', {'name': '甲', 'gender': 'male', 'class_name': '高一1班', 'grade': '小学一年级'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Student.objects.exists())

    def test_student_move_infers_new_grade_without_registrations(self):
        self.configure()
        student = Student.objects.create(name='甲', gender='male', class_name='高一1班', grade='高一')
        response = self.client.patch(f'/api/students/{student.pk}/', {'class_name': '一年级1班'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['grade'], '小学一年级')

    def test_custom_grade_filters_students_and_both_registration_types(self):
        self.configure()
        meet = SportsMeet.objects.create(name='测试')
        event = Event.objects.create(sports_meet=meet, name='跑步', event_type='track')
        student = Student.objects.create(name='甲', gender='male', class_name='高一1班', grade='高一')
        other = Student.objects.create(name='乙', gender='male', class_name='一年级1班', grade='小学一年级')
        for pupil in [student, other]:
            Registration.objects.create(event=event, student=pupil)
            TeamRegistration.objects.create(event=event, class_name=pupil.class_name)
        for url in ['/api/students/', '/api/registrations/', '/api/team-registrations/']:
            response = self.client.get(url, {'class_name': '高一'})
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data['count'], 1)

    def test_new_meet_uses_school_name_without_changing_old_meet(self):
        old = SportsMeet.objects.create(name='往届', school='旧校名')
        self.configure()
        response = self.client.post('/api/sports-meets/', {'name': '新运动会'}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['school'], '测试学校')
        old.refresh_from_db(); self.assertEqual(old.school, '旧校名')

    def test_template_contains_no_fake_pupils(self):
        import openpyxl
        self.configure()
        response = self.client.get('/api/students/export_template/')
        workbook = openpyxl.load_workbook(io.BytesIO(response.content))
        rows = list(workbook.active.values)
        self.assertEqual(rows[1][0], None)
        self.assertEqual(rows[1][4], '高一1班')


class BootstrapSchoolTests(TestCase):
    def run_command(self):
        call_command('bootstrap_school', school='新学校', username='new-admin', stdout=io.StringIO())

    @patch('accounts.management.commands.bootstrap_school.getpass.getpass', side_effect=['secure-pass-42', 'secure-pass-42'])
    def test_bootstrap_only_creates_school_and_admin(self, prompt):
        self.run_command()
        user = User.objects.get()
        self.assertEqual(user.role, 'admin')
        self.assertTrue(user.check_password('secure-pass-42'))
        self.assertEqual(SchoolProfile.objects.get().school_name, '新学校')
        self.assertFalse(SportsMeet.objects.exists()); self.assertFalse(Student.objects.exists())

    @patch('accounts.management.commands.bootstrap_school.getpass.getpass', side_effect=['short', 'short'])
    def test_weak_password_rolls_back_all_data(self, prompt):
        with self.assertRaises(CommandError): self.run_command()
        self.assertFalse(User.objects.exists()); self.assertFalse(SchoolProfile.objects.exists())

    @patch('accounts.management.commands.bootstrap_school.getpass.getpass', side_effect=['secure-pass-42', 'different-pass'])
    def test_confirmation_mismatch_rolls_back_all_data(self, prompt):
        with self.assertRaises(CommandError): self.run_command()
        self.assertFalse(User.objects.exists()); self.assertFalse(SchoolProfile.objects.exists())

    @patch('accounts.management.commands.bootstrap_school.getpass.getpass')
    def test_existing_business_data_blocks_bootstrap(self, prompt):
        meet = SportsMeet.objects.create(name='保留运动会')
        with self.assertRaises(CommandError): self.run_command()
        prompt.assert_not_called()
        self.assertTrue(SportsMeet.objects.filter(pk=meet.pk).exists())
        self.assertFalse(User.objects.exists()); self.assertFalse(SchoolProfile.objects.exists())

    @patch('accounts.management.commands.bootstrap_school.getpass.getpass')
    def test_existing_account_blocks_bootstrap(self, prompt):
        User.objects.create_user('existing', role='teacher')
        with self.assertRaises(CommandError): self.run_command()
        prompt.assert_not_called(); self.assertEqual(User.objects.count(), 1)


class DemoDataProtectionTests(TestCase):
    @override_settings(DEBUG=False)
    def test_demo_clear_is_refused_before_any_deletion_in_production(self):
        meet = SportsMeet.objects.create(name='生产数据')
        with self.assertRaises(CommandError): call_command('seed_data', clear=True, stdout=io.StringIO())
        self.assertTrue(SportsMeet.objects.filter(pk=meet.pk).exists())

    @override_settings(DEBUG=True)
    def test_demo_clear_is_refused_in_initialized_school_even_with_debug(self):
        SchoolProfile.objects.create(school_name='正式学校')
        meet = SportsMeet.objects.create(name='保留数据')
        with self.assertRaises(CommandError): call_command('seed_data', clear=True, stdout=io.StringIO())
        self.assertTrue(SportsMeet.objects.filter(pk=meet.pk).exists())

    def test_overall_points_api_can_be_requested_without_grade_rows(self):
        admin = User.objects.create_user('points-admin', role='admin')
        meet = SportsMeet.objects.create(name='积分测试')
        ClassPoints.objects.create(sports_meet=meet, class_name='高一1班', grade='高一', total_points=4)
        ClassPoints.objects.create(sports_meet=meet, class_name='高一1班', grade='', total_points=4)
        client = APIClient(); client.force_authenticate(admin)
        response = client.get('/api/class-points/', {'sports_meet': meet.pk, 'grade': ''})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['grade'], '')
