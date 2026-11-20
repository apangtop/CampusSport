import io
import math
from datetime import timedelta

import openpyxl
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from events.models import Event, Schedule, SportsMeet
from registration.models import Registration, Student, TeamRegistration
from scores.models import ClassPoints, Score, TeamScore
from scores.views import calculate_rank_and_points, recalculate_class_points


class SecurityRegressionTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user('admin', password='admin123', role='admin')
        self.teacher = User.objects.create_user('teacher', password='teacher123', role='teacher', class_name='2028级1班')
        self.referee = User.objects.create_user('ref', password='referee123', role='referee')
        self.other_referee = User.objects.create_user('other-ref', role='referee')
        self.meet = SportsMeet.objects.create(name='测试运动会', status='registration')
        self.event = Event.objects.create(sports_meet=self.meet, name='100米', event_type='track', gender='male', referee=self.referee)
        self.other_event = Event.objects.create(sports_meet=self.meet, name='200米', event_type='track', referee=self.other_referee)
        self.student = Student.objects.create(name='张三', gender='male', class_name=self.teacher.class_name, grade='2028级')
        self.other_student = Student.objects.create(name='李四', gender='male', class_name='2028级2班', grade='2028级')
        self.client = APIClient()
        self.client.force_authenticate(self.teacher)

    def ongoing(self):
        self.meet.status = 'ongoing'
        self.meet.save()

    def reg(self, event=None, student=None, status='approved'):
        return Registration.objects.create(event=event or self.event, student=student or self.student, status=status)

    def test_teacher_cannot_change_account_assignment(self):
        res = self.client.patch(f'/api/users/{self.teacher.pk}/', {'class_name': '2028级2班'}, format='json')
        self.assertEqual(res.status_code, 403)
        self.teacher.refresh_from_db()
        self.assertEqual(self.teacher.class_name, '2028级1班')

    def test_teacher_cannot_reset_password_without_old_password(self):
        res = self.client.post(f'/api/users/{self.teacher.pk}/reset_password/', {'new_password':'stolen123'}, format='json')
        self.assertEqual(res.status_code, 403)
        self.teacher.refresh_from_db()
        self.assertTrue(self.teacher.check_password('teacher123'))

    def test_admin_can_edit_account(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.patch(f'/api/users/{self.teacher.pk}/', {'phone':'123'}, format='json').status_code, 200)

    def test_teacher_cannot_move_student_to_another_class(self):
        res = self.client.patch(f'/api/students/{self.student.pk}/', {'class_name': '2028级2班'}, format='json')
        self.assertEqual(res.status_code, 403)
        self.student.refresh_from_db()
        self.assertEqual(self.student.class_name, self.teacher.class_name)

    def test_bulk_students_respects_class(self):
        before = Student.objects.count()
        res = self.client.post('/api/students/bulk/', {'students':[{'name':'越权', 'class_name':'2028级2班'}]}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(Student.objects.count(), before)
        self.assertTrue(res.data['errors'])

    def test_excel_import_cannot_modify_other_class(self):
        wb = openpyxl.Workbook()
        wb.active.append(['姓名','性别','学号','年级','班级'])
        wb.active.append(['李四','女','','2028级','2028级2班'])
        buf = io.BytesIO(); wb.save(buf); buf.seek(0); buf.name = 'students.xlsx'
        res = self.client.post('/api/students/import_excel/', {'file':buf}, format='multipart')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data['errors'])
        self.other_student.refresh_from_db()
        self.assertEqual(self.other_student.gender, 'male')

    def test_teacher_cannot_approve_individual_or_team(self):
        reg = self.reg(status='submitted')
        team = TeamRegistration.objects.create(event=self.event, class_name=self.teacher.class_name)
        for path in [f'/api/registrations/{reg.pk}/approve/', f'/api/team-registrations/{team.pk}/approve/',
                     '/api/registrations/approve_all/', '/api/team-registrations/approve_all/']:
            self.assertEqual(self.client.post(path, {}, format='json').status_code, 403, path)
        reg.refresh_from_db(); self.assertEqual(reg.status, 'submitted')

    def test_referee_cannot_create_registration(self):
        self.client.force_authenticate(self.referee)
        res = self.client.post('/api/registrations/', {'event':self.event.pk, 'student':self.student.pk}, format='json')
        self.assertEqual(res.status_code, 403)
        self.assertEqual(Registration.objects.count(), 0)

    def test_single_registration_enforces_class_gender_grade(self):
        for student in [self.other_student]:
            res = self.client.post('/api/registrations/', {'event':self.event.pk,'student':student.pk}, format='json')
            self.assertEqual(res.status_code, 403)
        self.student.gender = 'female'; self.student.save()
        self.assertEqual(self.client.post('/api/registrations/', {'event':self.event.pk,'student':self.student.pk}, format='json').status_code, 400)
        self.student.gender = 'male'; self.student.save()
        self.event.grade = '2027级'; self.event.save()
        self.assertEqual(self.client.post('/api/registrations/', {'event':self.event.pk,'student':self.student.pk}, format='json').status_code, 400)
        self.assertEqual(Registration.objects.count(), 0)

    def test_single_and_bulk_enforce_closed_registration(self):
        self.meet.registration_deadline = timezone.now()-timedelta(hours=1); self.meet.save()
        for path, data in [('/api/registrations/', {'event':self.event.pk,'student':self.student.pk}),
                           ('/api/registrations/bulk_register/', {'event_id':self.event.pk,'student_ids':[self.student.pk]})]:
            self.assertEqual(self.client.post(path, data, format='json').status_code, 400)
        self.assertEqual(Registration.objects.count(), 0)

    def test_single_and_bulk_enforce_limits(self):
        self.event.max_per_class=1; self.event.save()
        self.reg()
        student=Student.objects.create(name='王五', gender='male', class_name=self.teacher.class_name)
        self.assertEqual(self.client.post('/api/registrations/', {'event':self.event.pk,'student':student.pk}, format='json').status_code,400)
        self.assertEqual(self.client.post('/api/registrations/bulk_register/', {'event_id':self.event.pk,'student_ids':[student.pk]}, format='json').status_code,400)
        self.assertEqual(Registration.objects.count(),1)

    def test_meet_cap_cannot_be_overridden_by_event_cap(self):
        self.meet.max_events_per_person=1; self.meet.save(); self.reg()
        res=self.client.post('/api/registrations/', {'event':self.other_event.pk,'student':self.student.pk}, format='json')
        self.assertEqual(res.status_code,400)

    def test_bulk_existing_registration_is_idempotent(self):
        self.event.max_per_person=1; self.event.save(); reg=self.reg()
        res=self.client.post('/api/registrations/bulk_register/', {'event_id':self.event.pk,'student_ids':[self.student.pk]}, format='json')
        self.assertEqual(res.status_code,200); self.assertEqual(res.data['errors'],[])
        self.assertEqual(Registration.objects.count(),1)

    def test_team_rejects_other_class_members_and_manual_approval(self):
        self.event.event_type='relay'; self.event.team_size=1; self.event.save()
        res=self.client.post('/api/team-registrations/', {'event':self.event.pk, 'class_name':self.teacher.class_name,
                    'members':[self.other_student.pk],'status':'approved'}, format='json')
        self.assertEqual(res.status_code,400); self.assertEqual(TeamRegistration.objects.count(),0)
        res=self.client.post('/api/team-registrations/', {'event':self.event.pk, 'class_name':self.teacher.class_name,
                    'members':[self.student.pk],'status':'approved'}, format='json')
        self.assertEqual(res.status_code,201); self.assertEqual(res.data['status'],'submitted')

    def test_team_patch_cannot_change_class_or_bypass_deadline(self):
        self.event.event_type='relay'; self.event.team_size=1; self.event.save()
        team=TeamRegistration.objects.create(event=self.event,class_name=self.teacher.class_name); team.members.add(self.student)
        self.assertEqual(self.client.patch(f'/api/team-registrations/{team.pk}/',{'class_name':'2028级2班'},format='json').status_code,400)
        self.ongoing()
        self.assertEqual(self.client.patch(f'/api/team-registrations/{team.pk}/',{'lane':3},format='json').status_code,403)

    def test_rejected_score_create_does_not_write(self):
        self.ongoing(); reg=self.reg(event=self.other_event)
        self.client.force_authenticate(self.referee)
        res=self.client.post('/api/scores/', {'registration':reg.pk,'result_numeric':10},format='json')
        self.assertEqual(res.status_code,403); self.assertEqual(Score.objects.count(),0)

    def test_finished_meet_rejects_score_without_write(self):
        self.meet.status='finished'; self.meet.save(); reg=self.reg()
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.post('/api/scores/',{'registration':reg.pk,'result_numeric':10},format='json').status_code,403)
        self.assertEqual(Score.objects.count(),0)

    def test_batch_checks_every_registration_and_rolls_back(self):
        self.ongoing(); first=self.reg(); second=self.reg(event=self.other_event)
        self.client.force_authenticate(self.referee)
        res=self.client.post('/api/scores/batch_submit/', {'scores':[
            {'registration_id':first.pk,'result_numeric':10}, {'registration_id':second.pk,'result_numeric':20}]}, format='json')
        self.assertEqual(res.status_code,403); self.assertEqual(Score.objects.count(),0)

    def test_teacher_cannot_batch_score_or_advance(self):
        self.ongoing(); reg=self.reg()
        for path,data in [('/api/scores/batch_submit/',{'scores':[{'registration_id':reg.pk,'result_numeric':10}]}),
                          ('/api/scores/confirm_advancement/',{'event_id':self.event.pk}),
                          ('/api/scores/auto_advance_top/',{'event_id':self.event.pk}),
                          ('/api/scores/calculate_ranks/',{'event_id':self.event.pk}),
                          ('/api/class-points/recalculate/',{'sports_meet_id':self.meet.pk})]:
            self.assertEqual(self.client.post(path,data,format='json').status_code,403,path)

    def test_batch_rejects_bad_payloads_without_server_error(self):
        self.ongoing(); reg=self.reg(); self.client.force_authenticate(self.admin)
        for items in ['bad', [{}], [3], [{'registration_id':reg.pk,'stage':[]}],
                      [{'registration_id':reg.pk,'result_numeric':'bad'}],
                      [{'registration_id':reg.pk,'result_numeric':'Infinity'}]]:
            self.assertEqual(self.client.post('/api/scores/batch_submit/',{'scores':items},format='json').status_code,400)
        self.assertEqual(Score.objects.count(),0)

    def test_create_update_delete_refreshes_rank_and_total(self):
        self.ongoing(); first=self.reg(); second=self.reg(student=self.other_student)
        self.client.force_authenticate(self.admin)
        a=self.client.post('/api/scores/',{'registration':first.pk,'result_numeric':10},format='json')
        b=self.client.post('/api/scores/',{'registration':second.pk,'result_numeric':11},format='json')
        self.assertEqual(a.status_code,201); self.assertEqual(b.status_code,201)
        score=Score.objects.get(pk=b.data['id']); self.assertEqual(score.rank,2)
        self.assertEqual(self.client.delete(f"/api/scores/{a.data['id']}/").status_code,204)
        score.refresh_from_db(); self.assertEqual(score.rank,1)
        self.assertEqual(ClassPoints.objects.get(grade='',class_name=self.other_student.class_name).total_points,4)
        self.assertEqual(self.client.patch(f'/api/scores/{score.pk}/',{'result_numeric':None},format='json').status_code,200)
        score.refresh_from_db(); self.assertIsNone(score.rank); self.assertEqual(score.points,0)
        self.assertEqual(ClassPoints.objects.count(),0)

    def test_batch_recalculates_all_events(self):
        self.ongoing(); first=self.reg(); second=self.reg(event=self.other_event)
        self.client.force_authenticate(self.admin)
        res=self.client.post('/api/scores/batch_submit/',{'scores':[
            {'registration_id':first.pk,'result_numeric':10},{'registration_id':second.pk,'result_numeric':20}]},format='json')
        self.assertEqual(res.status_code,200)
        self.assertEqual(list(Score.objects.values_list('rank',flat=True)),[1,1])
        self.assertEqual(ClassPoints.objects.get(grade='').total_points,8)

    def test_numeric_zero_and_ties(self):
        self.ongoing(); a=self.reg(); b=self.reg(student=self.other_student)
        Score.objects.create(registration=a,result_numeric=0); Score.objects.create(registration=b,result_numeric=0)
        calculate_rank_and_points(self.event)
        self.assertEqual(list(Score.objects.values_list('rank',flat=True)),[1,1])

    def test_unknown_grade_does_not_duplicate_unique_total(self):
        self.ongoing(); self.student.class_name='初一1班';self.student.grade='';self.student.save()
        reg=self.reg(); Score.objects.create(registration=reg,result_numeric=10,rank=1,points=4)
        recalculate_class_points(self.meet)
        self.assertEqual(ClassPoints.objects.count(),1)
        self.assertEqual(ClassPoints.objects.get().grade,'')

    def test_two_stage_advancement_goes_to_final(self):
        self.ongoing();self.event.stage_type='two';self.event.save(); reg=self.reg()
        Score.objects.create(registration=reg,stage='preliminary',result_numeric=10,rank=1)
        self.client.force_authenticate(self.admin)
        res=self.client.post('/api/scores/confirm_advancement/',{'event_id':self.event.pk,'stage':'preliminary','registration_ids':[reg.pk]},format='json')
        self.assertEqual(res.status_code,200);reg.refresh_from_db();self.assertEqual(reg.schedule.stage,'final')

    def test_advancement_rejects_foreign_registrations(self):
        self.ongoing();self.event.stage_type='two';self.event.save();reg=self.reg(event=self.other_event)
        self.client.force_authenticate(self.admin)
        res=self.client.post('/api/scores/confirm_advancement/',{'event_id':self.event.pk,'stage':'preliminary','registration_ids':[reg.pk]},format='json')
        self.assertEqual(res.status_code,400);reg.refresh_from_db();self.assertIsNone(reg.schedule)
        self.assertEqual(Schedule.objects.count(),0)

    def test_invalid_auto_advancement_count(self):
        self.client.force_authenticate(self.admin)
        for count in ['bad',0,-1]:
            self.assertEqual(self.client.post('/api/scores/auto_advance_top/',{'event_id':self.event.pk,'advance_count':count},format='json').status_code,400)

    def test_team_scores_enforce_assignment_and_sort_winner_first(self):
        self.ongoing();self.event.event_type='team_confrontation';self.event.confrontation_format='bo3';self.event.save()
        a=TeamRegistration.objects.create(event=self.event,class_name=self.teacher.class_name,status='approved')
        b=TeamRegistration.objects.create(event=self.event,class_name=self.other_student.class_name,status='approved')
        self.client.force_authenticate(self.other_referee)
        self.assertEqual(self.client.post('/api/team-scores/',{'team_registration':a.pk,'result_numeric':2},format='json').status_code,403)
        self.assertEqual(TeamScore.objects.count(),0)
        self.client.force_authenticate(self.referee)
        res=self.client.post('/api/team-scores/',{'team_registration':a.pk,'result_numeric':2,
            'rounds_data':[{'round_number':1,'winner_class':a.class_name},{'round_number':3,'winner_class':a.class_name}]},format='json')
        self.assertEqual(res.status_code,201)
        self.assertEqual(self.client.post('/api/team-scores/',{'team_registration':b.pk,'result_numeric':1},format='json').status_code,201)
        score=TeamScore.objects.get(pk=res.data['id']);self.assertEqual(score.rank,1)
        res=self.client.patch(f'/api/team-scores/{score.pk}/',{'rounds_data':[{'round_number':2,'winner_class':a.class_name}]},format='json')
        self.assertEqual(res.status_code,200);self.assertEqual(list(score.rounds.values_list('round_number',flat=True)),[2])

    def test_schedule_partial_update_checks_existing_time(self):
        now=timezone.now();a=Schedule.objects.create(event=self.event,venue='A',scheduled_time=now)
        Schedule.objects.create(event=self.other_event,venue='B',scheduled_time=now)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.patch(f'/api/schedules/{a.pk}/',{'venue':'B'},format='json').status_code,400)

    def test_meet_partial_update_checks_existing_dates(self):
        self.meet.start_date=timezone.now().date();self.meet.save();self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.patch(f'/api/sports-meets/{self.meet.pk}/',{'end_date':str(self.meet.start_date-timedelta(days=1))},format='json').status_code,400)

    def test_lane_count_zero_does_not_clear_assignments(self):
        self.client.force_authenticate(self.admin); reg=self.reg();reg.lane=5;reg.save()
        for lanes in [0,'bad',-1]:
            self.assertEqual(self.client.post(f'/api/events/{self.event.pk}/auto_assign_lanes/',{'lanes_per_group':lanes},format='json').status_code,400)
        reg.refresh_from_db();self.assertEqual(reg.lane,5)

    def test_export_includes_teams_and_sanitizes_sheet_names_and_formulas(self):
        from reports.views import build_result_report_excel
        self.ongoing();self.event.name='100米/决赛';self.event.save();reg=self.reg()
        self.student.name='=1+1';self.student.save();Score.objects.create(registration=reg,result_numeric=10,result='10',points=4,rank=1)
        team=TeamRegistration.objects.create(event=self.other_event,class_name=self.teacher.class_name,status='approved')
        TeamScore.objects.create(team_registration=team,result='20',result_numeric=20,points=3,rank=2)
        recalculate_class_points(self.meet)
        wb=build_result_report_excel(self.meet)
        self.assertEqual(wb.worksheets[1]['B3'].data_type,'s')
        self.assertEqual(wb.worksheets[1]['B3'].value,'=1+1')
        self.assertEqual(wb.worksheets[2]['B3'].value,'团体')
        self.assertEqual(wb.worksheets[0].max_row,2)
        buf=io.BytesIO();wb.save(buf)

    def test_report_list_has_serializer(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get('/api/reports/').status_code,200)

    def test_score_rules_reject_nonfinite_and_negative(self):
        self.client.force_authenticate(self.admin)
        for rules in [{'1':-1},{'1':'NaN'},{'0':3}]:
            self.assertEqual(self.client.patch(f'/api/events/{self.event.pk}/',{'score_rules':rules},format='json').status_code,400)


    def test_delete_protected_student_returns_conflict(self):
        self.reg(); self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.delete(f'/api/students/{self.student.pk}/').status_code,409)
        self.assertTrue(Student.objects.filter(pk=self.student.pk).exists())

    def test_invalid_custom_action_ids_return_bad_request(self):
        self.client.force_authenticate(self.admin)
        for path, data in [('/api/scores/calculate_ranks/', {'event_id':'bad'}),
                           ('/api/scores/confirm_advancement/', {'event_id':[]}),
                           ('/api/class-points/recalculate/', {'sports_meet_id':'bad'}),
                           ('/api/registrations/approve_all/', {'event_id':'bad'})]:
            self.assertEqual(self.client.post(path,data,format='json').status_code,400,path)
        self.assertEqual(self.client.get('/api/reports/generate_result_report/?sports_meet_id=bad').status_code,400)

    def test_password_reset_requires_explicit_strong_password(self):
        self.client.force_authenticate(self.admin)
        for data in [{}, {'new_password':'123'}]:
            self.assertEqual(self.client.post(f'/api/users/{self.teacher.pk}/reset_password/', data, format='json').status_code,400)
        self.teacher.refresh_from_db();self.assertTrue(self.teacher.check_password('teacher123'))
        self.assertEqual(self.client.post(f'/api/users/{self.teacher.pk}/reset_password/',{'new_password':'updated123'},format='json').status_code,200)

    def test_teacher_team_results_are_scoped(self):
        self.ongoing();self.event.event_type='relay';self.event.save()
        for class_name in [self.teacher.class_name,self.other_student.class_name]:
            team=TeamRegistration.objects.create(event=self.event,class_name=class_name,status='approved')
            TeamScore.objects.create(team_registration=team,result_numeric=10)
        res=self.client.get(f'/api/team-scores/?sports_meet={self.meet.pk}')
        self.assertEqual(res.status_code,200);self.assertEqual(res.data['count'],1)
        self.assertEqual(res.data['results'][0]['class_name'],self.teacher.class_name)

    def test_team_completion_summary(self):
        self.ongoing();self.event.event_type='relay';self.event.save()
        team=TeamRegistration.objects.create(event=self.event,class_name=self.teacher.class_name,status='approved')
        TeamScore.objects.create(team_registration=team,result_numeric=10)
        self.client.force_authenticate(self.admin)
        row=self.client.get(f'/api/sports-meets/{self.meet.pk}/score_summary/').data[0]
        self.assertEqual((row['total'],row['scored'],row['complete']),(1,1,True))

    def test_reports_download_as_word_and_excel(self):
        self.client.force_authenticate(self.admin)
        for route,mime in [('generate_order_book','wordprocessingml.document'),('generate_result_report','spreadsheetml.sheet')]:
            res=self.client.get(f'/api/reports/{route}/?sports_meet_id={self.meet.pk}')
            self.assertEqual(res.status_code,200);self.assertIn(mime,res['Content-Type'])
            self.assertTrue(res.content.startswith(b'PK'))


    def test_password_change_revokes_access_and_refresh(self):
        self.client.force_authenticate(None)
        login=self.client.post('/api/auth/login/', {'username':'teacher','password':'teacher123'},format='json')
        self.assertEqual(login.status_code,200)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer '+login.data['access'])
        self.assertEqual(self.client.get('/api/users/me/').status_code,200)
        self.teacher.set_password('changed123');self.teacher.save()
        self.assertEqual(self.client.get('/api/users/me/').status_code,401)
        self.client.credentials()
        self.assertEqual(self.client.post('/api/auth/refresh/',{'refresh':login.data['refresh']},format='json').status_code,401)

    def test_disabled_account_cannot_refresh(self):
        self.client.force_authenticate(None)
        login=self.client.post('/api/auth/login/', {'username':'teacher','password':'teacher123'},format='json')
        self.teacher.is_active=False;self.teacher.save()
        self.assertEqual(self.client.post('/api/auth/refresh/',{'refresh':login.data['refresh']},format='json').status_code,401)


    def test_team_batch_is_atomic_and_recalculates(self):
        self.ongoing();self.event.event_type='relay';self.event.save()
        self.other_event.event_type='relay';self.other_event.save()
        a=TeamRegistration.objects.create(event=self.event,class_name=self.teacher.class_name,status='approved')
        b=TeamRegistration.objects.create(event=self.other_event,class_name=self.other_student.class_name,status='approved')
        items=[{'team_registration':a.pk,'result_numeric':10},{'team_registration':b.pk,'result_numeric':20}]
        self.client.force_authenticate(self.referee)
        self.assertEqual(self.client.post('/api/team-scores/batch_submit/',{'scores':items},format='json').status_code,403)
        self.assertEqual(TeamScore.objects.count(),0)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.post('/api/team-scores/batch_submit/',{'scores':items},format='json').status_code,200)
        self.assertEqual(TeamScore.objects.count(),2)
        self.assertEqual(list(TeamScore.objects.values_list('rank',flat=True)),[1,1])

    def test_teacher_cannot_batch_team_scores(self):
        self.assertEqual(self.client.post('/api/team-scores/batch_submit/',{'scores':[]},format='json').status_code,403)
