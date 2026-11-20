from types import SimpleNamespace
from django.test import TestCase
from django.http import Http404
from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.test import APIClient
from accounts.models import User
from events.models import SportsMeet, Event, Schedule
from registration.models import Student, Registration, TeamRegistration
from registration.serializers import StudentSerializer
from registration.views import StudentViewSet
from scores.models import Score, TeamScore
from scores.serializers import ScoreSerializer, TeamScoreSerializer
from scores.views import ScoreViewSet, TeamScoreViewSet


class ReliabilityRegressionTests(TestCase):
    def setUp(self):
        self.admin=User.objects.create_user('reliability-admin',role='admin')
        self.meet=SportsMeet.objects.create(name='测试',status='ongoing')
        self.event=Event.objects.create(sports_meet=self.meet,name='100米',event_type='track')
        self.student=Student.objects.create(name='甲',class_name='1班',gender='male')
        self.reg=Registration.objects.create(event=self.event,student=self.student,status='approved')
        self.client=APIClient();self.client.force_authenticate(self.admin)
        self.request=SimpleNamespace(user=self.admin,method='POST')

    def test_individual_create_rechecks_uniqueness_after_validation(self):
        serializer=ScoreSerializer(data={'registration':self.reg.pk,'result_numeric':10},context={'request':self.request})
        serializer.is_valid(raise_exception=True)
        existing=Score.objects.create(registration=self.reg,result_numeric=11)
        view=ScoreViewSet();view.request=self.request
        with self.assertRaises(ValidationError):view.perform_create(serializer)
        existing.refresh_from_db();self.assertEqual(existing.result_numeric,11);self.assertEqual(Score.objects.count(),1)

    def test_team_create_rechecks_uniqueness_after_validation(self):
        self.event.event_type='relay';self.event.save();team=TeamRegistration.objects.create(event=self.event,class_name='1班',status='approved')
        serializer=TeamScoreSerializer(data={'team_registration':team.pk,'result_numeric':10},context={'request':self.request})
        serializer.is_valid(raise_exception=True);TeamScore.objects.create(team_registration=team,result_numeric=11)
        view=TeamScoreViewSet();view.request=self.request
        with self.assertRaises(ValidationError):view.perform_create(serializer)
        self.assertEqual(TeamScore.objects.count(),1)

    def test_score_deleted_after_validation_returns_not_found(self):
        score=Score.objects.create(registration=self.reg,result_numeric=10)
        serializer=ScoreSerializer(score,data={'result_numeric':11},partial=True,context={'request':self.request})
        serializer.is_valid(raise_exception=True);score.delete()
        view=ScoreViewSet();view.request=self.request
        with self.assertRaises(Http404):view.perform_update(serializer)

    def test_same_student_identifier_is_rejected_by_regular_create(self):
        self.student.student_id='001';self.student.save()
        res=self.client.post('/api/students/',{'name':'不同姓名','student_id':'001','class_name':'1班','gender':'male'},format='json')
        self.assertEqual(res.status_code,400);self.assertEqual(Student.objects.count(),1)

    def test_student_create_rechecks_identity_after_validation(self):
        serializer=StudentSerializer(data={'name':'乙','student_id':'002','class_name':'1班','gender':'male'},context={'request':self.request})
        serializer.is_valid(raise_exception=True);Student.objects.create(name='丙',student_id='002',class_name='1班',gender='male')
        view=StudentViewSet();view.request=self.request
        with self.assertRaises(ValidationError):view.perform_create(serializer)
        self.assertEqual(Student.objects.filter(student_id='002').count(),1)

    def test_student_identity_has_database_unique_constraint(self):
        Student.objects.create(name='乙',student_id='003',class_name='1班',gender='male')
        with self.assertRaises(IntegrityError),transaction.atomic():Student.objects.create(name='丙',student_id='003',class_name='1班',gender='male')

    def test_missing_identifiers_allow_multiple_students(self):
        for name in ['乙','丙']:
            self.assertEqual(self.client.post('/api/students/',{'name':name,'student_id':'','class_name':'1班','gender':'male'},format='json').status_code,201)
        self.assertEqual(Student.objects.filter(class_name='1班').count(),3)

    def test_same_identifier_in_different_classes_remains_allowed(self):
        for cls in ['2班','3班']:
            self.assertEqual(self.client.post('/api/students/',{'name':'乙','student_id':'004','class_name':cls,'gender':'male'},format='json').status_code,201)

    def test_schedule_identity_has_database_unique_constraint(self):
        Schedule.objects.create(event=self.event,stage='final',group_number=1)
        with self.assertRaises(IntegrityError),transaction.atomic():Schedule.objects.create(event=self.event,stage='final',group_number=1)

    def test_round_identity_has_database_unique_constraint(self):
        team=TeamRegistration.objects.create(event=self.event,class_name='1班',status='approved');score=TeamScore.objects.create(team_registration=team)
        score.rounds.create(round_number=1,winner_class='1班')
        with self.assertRaises(IntegrityError),transaction.atomic():score.rounds.create(round_number=1,winner_class='1班')

    def prelim_and_advance(self):
        self.event.stage_type='two';self.event.save()
        schedule=Schedule.objects.create(event=self.event,stage='preliminary',group_number=3)
        self.reg.schedule=schedule;self.reg.lane=4;self.reg.save()
        result=self.client.post('/api/scores/',{'registration':self.reg.pk,'stage':'preliminary','result_numeric':10},format='json')
        self.assertEqual(result.status_code,201)
        self.assertEqual(self.client.post('/api/scores/confirm_advancement/',{'event_id':self.event.pk,'stage':'preliminary','registration_ids':[self.reg.pk]},format='json').status_code,200)
        return schedule,result.data['id']

    def test_previous_stage_participants_keep_recorded_group_and_lane(self):
        schedule,_=self.prelim_and_advance()
        row=self.client.get(f'/api/events/{self.event.pk}/participants/?stage=preliminary').data[0]
        self.assertEqual(row['schedule'],schedule.pk);self.assertEqual(row['lane'],4)
        self.assertEqual(row['schedule_info']['group_number'],3)

    def test_scored_historical_schedule_cannot_be_deleted_after_advancement(self):
        schedule,_=self.prelim_and_advance()
        self.assertEqual(self.client.delete(f'/api/schedules/{schedule.pk}/').status_code,400)
        self.assertTrue(Schedule.objects.filter(pk=schedule.pk).exists())

    def test_score_correction_preserves_recorded_schedule_snapshot(self):
        schedule,sid=self.prelim_and_advance()
        self.assertEqual(self.client.patch(f'/api/scores/{sid}/',{'result_numeric':11},format='json').status_code,200)
        row=self.client.get(f'/api/events/{self.event.pk}/participants/?stage=preliminary').data[0]
        self.assertEqual((row['schedule'],row['lane']),(schedule.pk,4))

    def test_client_cannot_forge_score_schedule_or_lane(self):
        schedule=Schedule.objects.create(event=self.event,stage='final',group_number=2)
        res=self.client.post('/api/scores/',{'registration':self.reg.pk,'result_numeric':10,'schedule':schedule.pk,'lane':99},format='json')
        self.assertEqual(res.status_code,201)
        self.assertIsNone(res.data['schedule']);self.assertIsNone(res.data['lane'])

    def test_scored_stage_assignments_cannot_be_changed(self):
        schedule=Schedule.objects.create(event=self.event,stage='final');self.reg.schedule=schedule;self.reg.lane=1;self.reg.save()
        self.assertEqual(self.client.post('/api/scores/',{'registration':self.reg.pk,'result_numeric':10},format='json').status_code,201)
        self.assertEqual(self.client.patch(f'/api/registrations/{self.reg.pk}/',{'lane':3},format='json').status_code,400)
        self.reg.refresh_from_db();self.assertEqual(self.reg.lane,1)

    def test_invalid_team_stage_is_rejected_by_participants(self):
        self.event.event_type='relay';self.event.save()
        self.assertEqual(self.client.get(f'/api/events/{self.event.pk}/participants/?stage=semifinal').status_code,400)

    def test_team_summary_does_not_expect_inapplicable_stage(self):
        self.event.event_type='relay';self.event.save();TeamRegistration.objects.create(event=self.event,class_name='1班',status='approved')
        row=self.client.get(f'/api/sports-meets/{self.meet.pk}/score_summary/?stage=semifinal').data[0]
        self.assertEqual((row['total'],row['scored']),(0,0))

    def test_team_previous_stage_group_survives_manual_next_stage_assignment(self):
        self.event.event_type='relay';self.event.stage_type='two';self.event.save()
        old=Schedule.objects.create(event=self.event,stage='preliminary',group_number=2)
        next_schedule=Schedule.objects.create(event=self.event,stage='final')
        team=TeamRegistration.objects.create(event=self.event,class_name='1班',status='approved',schedule=old,lane=3)
        self.assertEqual(self.client.post('/api/team-scores/',{'team_registration':team.pk,'stage':'preliminary','result_numeric':10},format='json').status_code,201)
        self.assertEqual(self.client.patch(f'/api/team-registrations/{team.pk}/',{'schedule':next_schedule.pk,'lane':1},format='json').status_code,200)
        row=self.client.get(f'/api/events/{self.event.pk}/participants/?stage=preliminary').data[0]
        self.assertEqual((row['schedule'],row['lane']),(old.pk,3))
        self.assertEqual(self.client.delete(f'/api/schedules/{old.pk}/').status_code,400)

    def test_duplicate_student_partial_update_keeps_original_identity(self):
        self.student.student_id='100';self.student.save()
        other=Student.objects.create(name='乙',class_name='1班',gender='male',student_id='200')
        self.assertEqual(self.client.patch(f'/api/students/{other.pk}/',{'student_id':'100'},format='json').status_code,400)
        other.refresh_from_db();self.assertEqual(other.student_id,'200')

    def test_stage_history_does_not_query_once_per_student(self):
        from django.test.utils import CaptureQueriesContext
        from django.db import connection
        schedule=Schedule.objects.create(event=self.event,stage='final')
        for i in range(8):
            student=Student.objects.create(name=str(i),class_name='2班',gender='male')
            reg=Registration.objects.create(event=self.event,student=student,status='approved',schedule=schedule,lane=i+1)
            self.client.post('/api/scores/',{'registration':reg.pk,'result_numeric':10+i},format='json')
        with CaptureQueriesContext(connection) as queries:
            res=self.client.get(f'/api/events/{self.event.pk}/participants/?stage=final')
        self.assertEqual(res.status_code,200)
        score_selects=[q['sql'] for q in queries if 'FROM "scores_score"' in q['sql']]
        self.assertEqual(len(score_selects),1)

    def test_historical_scored_schedule_stage_and_group_cannot_change(self):
        schedule,_=self.prelim_and_advance()
        for data in [{'stage':'final'},{'group_number':9}]:
            self.assertEqual(self.client.patch(f'/api/schedules/{schedule.pk}/',data,format='json').status_code,400)

    def test_direct_historical_schedule_delete_is_protected(self):
        from django.db.models.deletion import ProtectedError
        schedule,_=self.prelim_and_advance()
        with self.assertRaises(ProtectedError):schedule.delete()

    def test_student_deleted_after_validation_returns_not_found(self):
        other=Student.objects.create(name='乙',gender='male',class_name='2班')
        serializer=StudentSerializer(other,data={'name':'丙'},partial=True,context={'request':self.request})
        serializer.is_valid(raise_exception=True);other.delete()
        view=StudentViewSet();view.request=self.request
        with self.assertRaises(Http404):view.perform_update(serializer)

    def test_account_edit_does_not_restore_stale_password_or_active_state(self):
        from accounts.serializers import UserUpdateSerializer
        from accounts.views import UserViewSet
        user=User.objects.create_user('target-user',role='teacher',password='old-pass-123')
        serializer=UserUpdateSerializer(user,data={'real_name':'新姓名'},partial=True,context={'request':self.request})
        serializer.is_valid(raise_exception=True)
        fresh=User.objects.get(pk=user.pk);fresh.set_password('new-pass-123');fresh.is_active=False;fresh.save()
        view=UserViewSet();view.request=self.request;view.perform_update(serializer)
        user.refresh_from_db();self.assertTrue(user.check_password('new-pass-123'));self.assertFalse(user.is_active)

    def test_account_deleted_after_validation_cannot_be_resurrected(self):
        from accounts.serializers import UserUpdateSerializer
        from accounts.views import UserViewSet
        user=User.objects.create_user('deleted-user',role='teacher')
        serializer=UserUpdateSerializer(user,data={'real_name':'名字'},partial=True,context={'request':self.request})
        serializer.is_valid(raise_exception=True);user.delete()
        view=UserViewSet();view.request=self.request
        with self.assertRaises(Http404):view.perform_update(serializer)
        self.assertFalse(User.objects.filter(username='deleted-user').exists())
