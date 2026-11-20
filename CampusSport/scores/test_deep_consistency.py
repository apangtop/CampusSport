import io
import openpyxl
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from accounts.models import User
from events.models import SportsMeet, Event, Schedule
from registration.models import Student, Registration, TeamRegistration
from scores.models import Score, TeamScore, ClassPoints


class DeepConsistencyTests(TestCase):
    def setUp(self):
        self.admin=User.objects.create_user('deep-admin',role='admin')
        self.referee=User.objects.create_user('deep-ref',role='referee')
        self.client=APIClient();self.client.force_authenticate(self.admin)
        self.meet=SportsMeet.objects.create(name='运动会',status='ongoing')
        self.event=Event.objects.create(sports_meet=self.meet,name='拔河',event_type='team_confrontation',confrontation_format='bo3',referee=self.referee)
        self.a=TeamRegistration.objects.create(event=self.event,class_name='2028级1班',status='approved')
        self.b=TeamRegistration.objects.create(event=self.event,class_name='2028级2班',status='approved')

    def team_data(self,team,numeric,numbers):
        return {'team_registration':team.pk,'stage':'final','result_numeric':numeric,
            'rounds_data':[{'round_number':n,'winner_class':team.class_name} for n in numbers]}

    def pair(self,a,b):
        return self.client.post('/api/team-scores/batch_submit/',{'scores':[a,b]},format='json')

    def track(self,stage='single'):
        event=Event.objects.create(sports_meet=self.meet,name='100米',event_type='track',stage_type=stage)
        student=Student.objects.create(name='张三',gender='male',class_name='2028级1班',grade='2028级')
        reg=Registration.objects.create(event=event,student=student,status='approved')
        return event,student,reg

    def test_confrontation_wins_must_match_round_records(self):
        self.assertEqual(self.client.post('/api/team-scores/',self.team_data(self.a,2,[1]),format='json').status_code,400)
        self.assertFalse(TeamScore.objects.exists())

    def test_confrontation_fractional_or_excess_wins_rejected(self):
        for value in [1.5,3,4]:
            self.assertEqual(self.client.post('/api/team-scores/',{'team_registration':self.a.pk,'result_numeric':value},format='json').status_code,400)

    def test_rounds_only_patch_updates_numeric_and_points(self):
        score=TeamScore.objects.create(team_registration=self.a,result_numeric=2)
        score.rounds.create(round_number=1,winner_class=self.a.class_name);score.rounds.create(round_number=2,winner_class=self.a.class_name)
        res=self.client.patch(f'/api/team-scores/{score.pk}/',{'rounds_data':[]},format='json')
        self.assertEqual(res.status_code,200);score.refresh_from_db();self.assertEqual(score.result_numeric,0)

    def test_numeric_patch_cannot_diverge_from_existing_rounds(self):
        score=TeamScore.objects.create(team_registration=self.a,result_numeric=2)
        score.rounds.create(round_number=1,winner_class=self.a.class_name);score.rounds.create(round_number=2,winner_class=self.a.class_name)
        self.assertEqual(self.client.patch(f'/api/team-scores/{score.pk}/',{'result_numeric':1},format='json').status_code,400)

    def test_paired_rounds_cannot_have_two_winners_for_same_round(self):
        res=self.pair(self.team_data(self.a,2,[1,2]),self.team_data(self.b,1,[2]))
        self.assertEqual(res.status_code,400);self.assertEqual(TeamScore.objects.count(),0)

    def test_paired_rounds_cannot_skip_a_round(self):
        self.assertEqual(self.pair(self.team_data(self.a,2,[1,3]),self.team_data(self.b,0,[])).status_code,400)

    def test_paired_rounds_stop_when_match_is_won(self):
        self.assertEqual(self.pair(self.team_data(self.a,2,[1,2]),self.team_data(self.b,1,[3])).status_code,400)

    def test_valid_paired_result_is_atomic(self):
        self.assertEqual(self.pair(self.team_data(self.a,2,[1,3]),self.team_data(self.b,1,[2])).status_code,200)
        self.assertEqual(TeamScore.objects.count(),2)

    def test_teams_for_personal_event_cannot_receive_team_score(self):
        event,_,_=self.track();team=TeamRegistration.objects.create(event=event,class_name='1班',status='approved')
        self.assertEqual(self.client.post('/api/team-scores/',{'team_registration':team.pk,'result_numeric':10},format='json').status_code,400)

    def test_three_stage_final_requires_entire_qualification_chain(self):
        event,_,reg=self.track('three');Score.objects.create(registration=reg,stage='semifinal',result_numeric=10,is_advanced=True)
        self.assertEqual(self.client.post('/api/scores/',{'registration':reg.pk,'stage':'final','result_numeric':10},format='json').status_code,400)

    def test_recalculate_rebuilds_stale_project_points(self):
        event,_,reg=self.track();score=Score.objects.create(registration=reg,result_numeric=10,rank=8,points=999)
        res=self.client.post('/api/class-points/recalculate/',{'sports_meet_id':self.meet.pk},format='json')
        self.assertEqual(res.status_code,200);score.refresh_from_db();self.assertEqual((score.rank,score.points),(1,4))
        self.assertEqual(ClassPoints.objects.get(grade='',class_name='2028级1班').total_points,4)

    def test_finishing_meet_rebuilds_stale_totals(self):
        _,_,reg=self.track();Score.objects.create(registration=reg,result_numeric=10,rank=1,points=999)
        self.assertEqual(self.client.post(f'/api/sports-meets/{self.meet.pk}/set_status/',{'status':'finished'},format='json').status_code,200)
        self.assertEqual(ClassPoints.objects.get(grade='',class_name='2028级1班').total_points,4)

    def test_bulk_same_name_different_ids_create_two_students(self):
        res=self.client.post('/api/students/bulk/',{'class_name':'1班','students':[{'name':'同名','student_id':'001'},{'name':'同名','student_id':'002'}]},format='json')
        self.assertEqual(res.status_code,200);self.assertEqual(res.data['created'],2)

    def test_bulk_malformed_items_are_reported_without_crash(self):
        res=self.client.post('/api/students/bulk/',{'class_name':'1班','students':[None,3,{'name':None},{'name':'有效','gender':'男'}]},format='json')
        self.assertEqual(res.status_code,200);self.assertEqual(res.data['created'],1);self.assertEqual(len(res.data['errors']),3)

    def test_bulk_rejects_non_list_container(self):
        self.assertEqual(self.client.post('/api/students/bulk/',{'students':'bad'},format='json').status_code,400)

    def test_bulk_ambiguous_same_name_without_id_returns_error(self):
        for sid in ['001','002']:Student.objects.create(name='同名',class_name='1班',gender='male',student_id=sid)
        res=self.client.post('/api/students/bulk/',{'class_name':'1班','students':[{'name':'同名'}]},format='json')
        self.assertEqual(res.status_code,200);self.assertEqual(len(res.data['errors']),1);self.assertEqual(res.data['created'],0)

    def test_bulk_cannot_bypass_student_field_validation(self):
        res=self.client.post('/api/students/bulk/',{'class_name':'1班','students':[{'name':'长'*51}]},format='json')
        self.assertEqual(res.status_code,200);self.assertEqual(res.data['created'],0);self.assertTrue(res.data['errors'])

    def test_existing_student_id_with_different_name_reports_conflict(self):
        Student.objects.create(name='原姓名',class_name='1班',gender='male',student_id='001')
        res=self.client.post('/api/students/bulk/',{'class_name':'1班','students':[{'name':'不同姓名','student_id':'001'}]},format='json')
        self.assertEqual(res.status_code,200);self.assertEqual(res.data['created'],0);self.assertTrue(res.data['errors'])

    def test_last_admin_cannot_be_disabled(self):
        self.assertEqual(self.client.patch(f'/api/users/{self.admin.pk}/',{'is_active':False},format='json').status_code,400)
        self.admin.refresh_from_db();self.assertTrue(self.admin.is_active)

    def test_last_admin_cannot_be_deleted(self):
        self.assertEqual(self.client.delete(f'/api/users/{self.admin.pk}/').status_code,400)
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())

    def test_one_of_two_admins_can_be_disabled(self):
        User.objects.create_user('backup-admin',role='admin')
        self.assertEqual(self.client.patch(f'/api/users/{self.admin.pk}/',{'is_active':False},format='json').status_code,200)

    def test_report_filename_handles_control_characters_and_quotes(self):
        self.meet.name='名字"\n换行';self.meet.save()
        for route in ['generate_order_book','generate_result_report']:
            res=self.client.get(f'/api/reports/{route}/?sports_meet_id={self.meet.pk}')
            self.assertEqual(res.status_code,200);self.assertNotIn('\n',res['Content-Disposition'])

    def test_score_rule_aliases_do_not_silently_drop_points(self):
        event,_,reg=self.track();Score.objects.create(registration=reg,result_numeric=10)
        res=self.client.patch(f'/api/events/{event.pk}/',{'score_rules':{'01':9}},format='json')
        self.assertEqual(res.status_code,200);self.assertEqual(Score.objects.get(registration=reg).points,9)

    def test_score_rule_duplicate_rank_aliases_are_rejected(self):
        self.assertEqual(self.client.patch(f'/api/events/{self.event.pk}/',{'score_rules':{'1':4,'01':8}},format='json').status_code,400)

    def test_match_format_cannot_change_after_results_exist(self):
        TeamScore.objects.create(team_registration=self.a,result_numeric=2)
        self.assertEqual(self.client.patch(f'/api/events/{self.event.pk}/',{'confrontation_format':'bo5'},format='json').status_code,400)

    def test_list_filters_validate_ids_without_server_error(self):
        for route in ['/api/events/','/api/schedules/','/api/registrations/','/api/team-registrations/','/api/scores/','/api/team-scores/','/api/class-points/','/api/reports/','/api/history/points/']:
            self.assertEqual(self.client.get(route+'?sports_meet=bad').status_code,400,route)

    def test_custom_actions_reject_array_bodies(self):
        for route in ['/api/scores/batch_submit/','/api/team-scores/batch_submit/','/api/scores/calculate_ranks/','/api/scores/confirm_advancement/','/api/scores/auto_advance_top/','/api/class-points/recalculate/',f'/api/sports-meets/{self.meet.pk}/set_status/',f'/api/events/{self.event.pk}/auto_assign_lanes/',f'/api/users/{self.admin.pk}/reset_password/']:
            self.assertEqual(self.client.post(route,[],format='json').status_code,400,route)

    def test_group_lane_count_cannot_be_fractional(self):
        self.assertEqual(self.client.post(f'/api/events/{self.event.pk}/auto_assign_lanes/',{'lanes_per_group':2.5},format='json').status_code,400)

    def test_advancement_count_cannot_be_fractional(self):
        event,_,_=self.track('two')
        self.assertEqual(self.client.post('/api/scores/auto_advance_top/',{'event_id':event.pk,'advance_count':1.5},format='json').status_code,400)

    def test_aggregate_does_not_count_unqualified_legacy_final(self):
        from scores.views import recalculate_class_points
        _,_,reg=self.track('two');Score.objects.create(registration=reg,result_numeric=10,rank=1,points=4)
        recalculate_class_points(self.meet)
        self.assertFalse(ClassPoints.objects.exists())

    def test_aggregate_does_not_count_team_score_for_personal_event(self):
        from scores.views import recalculate_class_points
        event,_,_=self.track();team=TeamRegistration.objects.create(event=event,class_name='1班',status='approved')
        TeamScore.objects.create(team_registration=team,result_numeric=10,rank=1,points=7)
        recalculate_class_points(self.meet);self.assertFalse(ClassPoints.objects.exists())

    def test_rebuild_clears_legacy_wrong_score_kind_and_stage(self):
        event,_,reg=self.track();team=TeamRegistration.objects.create(event=event,class_name='1班',status='approved')
        wrong=TeamScore.objects.create(team_registration=team,result_numeric=10,rank=1,points=9)
        invalid_stage=Score.objects.create(registration=reg,stage='semifinal',result_numeric=10,rank=1,points=9)
        self.client.post('/api/class-points/recalculate/',{'sports_meet_id':self.meet.pk},format='json')
        wrong.refresh_from_db();invalid_stage.refresh_from_db()
        self.assertEqual((wrong.rank,wrong.points,invalid_stage.rank,invalid_stage.points),(None,0,None,0))

    def test_bo5_win_limit_and_complete_pair(self):
        self.event.confrontation_format='bo5';self.event.save()
        self.assertEqual(self.pair(self.team_data(self.a,3,[1,3,5]),self.team_data(self.b,2,[2,4])).status_code,200)

    def test_incomplete_pair_is_not_saved(self):
        self.assertEqual(self.pair(self.team_data(self.a,1,[1]),self.team_data(self.b,1,[2])).status_code,400)
        self.assertFalse(TeamScore.objects.exists())

    def test_exact_duplicate_student_request_is_idempotent(self):
        data={'class_name':'1班','students':[{'name':'姓名','student_id':'001','gender':'男'}]}
        self.assertEqual(self.client.post('/api/students/bulk/',data,format='json').data['created'],1)
        res=self.client.post('/api/students/bulk/',data,format='json')
        self.assertEqual((res.data['created'],res.data['unchanged']),(0,1));self.assertEqual(res.data['errors'],[])

    def test_scoring_product_overflow_is_rejected_without_rule_change(self):
        before=self.event.score_rules
        res=self.client.patch(f'/api/events/{self.event.pk}/',{'score_rules':{'1':1e308},'score_multiplier':2},format='json')
        self.assertEqual(res.status_code,400);self.event.refresh_from_db();self.assertEqual(self.event.score_rules,before)

    def test_aggregate_overflow_rolls_back_existing_board(self):
        from scores.views import recalculate_class_points
        from rest_framework.exceptions import ValidationError
        _,student,reg=self.track();Score.objects.create(registration=reg,result_numeric=10,rank=1,points=1e308)
        other=Event.objects.create(sports_meet=self.meet,name='另一个项目',event_type='track')
        second=Registration.objects.create(event=other,student=student,status='approved')
        Score.objects.create(registration=second,result_numeric=11,rank=1,points=1e308)
        board=ClassPoints.objects.create(sports_meet=self.meet,class_name=student.class_name,total_points=4,rank=1)
        with self.assertRaises(ValidationError):recalculate_class_points(self.meet)
        board.refresh_from_db();self.assertEqual(board.total_points,4)

    def test_rejected_member_round_update_does_not_clear_old_rounds(self):
        score=TeamScore.objects.create(team_registration=self.a,result_numeric=1)
        score.rounds.create(round_number=1,winner_class=self.a.class_name)
        res=self.client.patch(f'/api/team-scores/{score.pk}/',{'rounds_data':[{'round_number':1,'winner_class':self.b.class_name}]},format='json')
        self.assertEqual(res.status_code,400);self.assertEqual(score.rounds.get().winner_class,self.a.class_name)
