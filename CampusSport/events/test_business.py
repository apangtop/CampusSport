from django.test import TestCase
from rest_framework.test import APIClient
from accounts.models import User
from events.models import SportsMeet, Event, Schedule
from registration.models import Student, Registration, TeamRegistration
from scores.models import Score, TeamScore, ClassPoints
from scores.views import recalculate_class_points


class BusinessWorkflowTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user('workflow-admin', role='admin')
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        self.meet = SportsMeet.objects.create(name='运动会', status='ongoing')
        self.event = Event.objects.create(sports_meet=self.meet, name='100米', event_type='track', stage_type='two')
        self.regs = []
        for i in range(3):
            student = Student.objects.create(name=str(i), gender='male', class_name=f'初一{i+1}班', grade='初一')
            self.regs.append(Registration.objects.create(event=self.event, student=student, status='approved'))

    def advance(self, ids):
        return self.client.post('/api/scores/confirm_advancement/', {'event_id':self.event.pk, 'stage':'preliminary', 'registration_ids':ids}, format='json')

    def prelim(self):
        for i, reg in enumerate(self.regs):
            Score.objects.create(registration=reg, stage='preliminary', result_numeric=10+i, rank=i+1)

    def test_unadvanced_registration_cannot_enter_final(self):
        res = self.client.post('/api/scores/', {'registration':self.regs[0].pk,'stage':'final','result_numeric':10},format='json')
        self.assertEqual(res.status_code,400)
        self.assertEqual(Score.objects.count(),0)

    def test_assignment_alone_does_not_grant_advancement(self):
        schedule=Schedule.objects.create(event=self.event,stage='final')
        self.regs[0].schedule=schedule;self.regs[0].save()
        self.test_unadvanced_registration_cannot_enter_final()

    def test_advanced_registration_can_enter_final(self):
        self.prelim();self.assertEqual(self.advance([self.regs[0].pk]).status_code,200)
        self.assertEqual(self.client.post('/api/scores/',{'registration':self.regs[0].pk,'stage':'final','result_numeric':10},format='json').status_code,201)

    def test_reconfirmation_removes_previous_next_stage_assignments(self):
        self.prelim();self.advance([self.regs[0].pk,self.regs[1].pk]);self.advance([self.regs[0].pk])
        self.regs[1].refresh_from_db();self.assertIsNone(self.regs[1].schedule);self.assertIsNone(self.regs[1].lane)

    def test_reconfirmation_cannot_remove_scored_finalist(self):
        self.prelim();self.advance([self.regs[0].pk]);Score.objects.create(registration=self.regs[0],stage='final',result_numeric=10)
        self.assertEqual(self.advance([self.regs[1].pk]).status_code,400)
        self.assertTrue(Score.objects.get(registration=self.regs[0],stage='preliminary').is_advanced)

    def test_reconfirm_same_list_preserves_existing_group_and_lane(self):
        self.prelim();self.advance([self.regs[0].pk]);schedule=Schedule.objects.create(event=self.event,stage='final',group_number=2)
        Registration.objects.filter(pk=self.regs[0].pk).update(schedule=schedule,lane=4)
        self.advance([self.regs[0].pk]);self.regs[0].refresh_from_db()
        self.assertEqual((self.regs[0].schedule_id,self.regs[0].lane),(schedule.pk,4))

    def test_auto_assignment_only_includes_advanced_finalists(self):
        self.prelim();self.advance([self.regs[0].pk])
        res=self.client.post(f'/api/events/{self.event.pk}/auto_assign_lanes/',{'stage':'final'},format='json')
        self.assertEqual(res.status_code,200)
        self.regs[1].refresh_from_db();self.assertIsNone(self.regs[1].schedule)

    def test_auto_assignment_rejects_final_without_advancement(self):
        res=self.client.post(f'/api/events/{self.event.pk}/auto_assign_lanes/',{'stage':'final'},format='json')
        self.assertEqual(res.status_code,400)
        self.assertEqual(Schedule.objects.count(),0)

    def test_auto_assignment_rejects_stage_with_recorded_results(self):
        self.prelim()
        self.assertEqual(self.client.post(f'/api/events/{self.event.pk}/auto_assign_lanes/',{'stage':'preliminary'},format='json').status_code,400)

    def test_participants_stage_filter_uses_advancement(self):
        self.prelim();self.advance([self.regs[0].pk])
        res=self.client.get(f'/api/events/{self.event.pk}/participants/?stage=final')
        self.assertEqual([r['id'] for r in res.data],[self.regs[0].pk])

    def test_completion_counts_finalists_instead_of_all_registrations(self):
        self.prelim();self.advance([self.regs[0].pk]);Score.objects.create(registration=self.regs[0],stage='final',result_numeric=10)
        row=self.client.get(f'/api/sports-meets/{self.meet.pk}/score_summary/?stage=final').data[0]
        self.assertEqual((row['total'],row['scored'],row['complete']),(1,1,True))

    def test_result_correction_revokes_unscored_advancement(self):
        self.prelim();self.advance([self.regs[0].pk]);score=Score.objects.get(registration=self.regs[0],stage='preliminary')
        self.assertEqual(self.client.patch(f'/api/scores/{score.pk}/',{'result_numeric':99},format='json').status_code,200)
        score.refresh_from_db();self.assertFalse(score.is_advanced)
        self.regs[0].refresh_from_db();self.assertIsNone(self.regs[0].schedule)

    def test_cannot_change_source_result_after_final_recorded(self):
        self.prelim();self.advance([self.regs[0].pk]);Score.objects.create(registration=self.regs[0],stage='final',result_numeric=10)
        score=Score.objects.get(registration=self.regs[0],stage='preliminary')
        self.assertEqual(self.client.patch(f'/api/scores/{score.pk}/',{'result_numeric':99},format='json').status_code,400)
        score.refresh_from_db();self.assertEqual(score.result_numeric,10)

    def test_cannot_delete_source_result_after_final_recorded(self):
        self.prelim();self.advance([self.regs[0].pk]);Score.objects.create(registration=self.regs[0],stage='final',result_numeric=10)
        score=Score.objects.get(registration=self.regs[0],stage='preliminary')
        self.assertEqual(self.client.delete(f'/api/scores/{score.pk}/').status_code,400)
        self.assertTrue(Score.objects.filter(pk=score.pk).exists())

    def test_event_with_registrations_cannot_move_to_other_meet(self):
        other=SportsMeet.objects.create(name='另一届')
        self.assertEqual(self.client.patch(f'/api/events/{self.event.pk}/',{'sports_meet':other.pk},format='json').status_code,400)

    def test_event_with_registrations_cannot_change_gender(self):
        self.assertEqual(self.client.patch(f'/api/events/{self.event.pk}/',{'gender':'female'},format='json').status_code,400)

    def test_event_with_results_cannot_change_unit_or_stage_type(self):
        self.prelim()
        for data in [{'result_unit':'meter'},{'stage_type':'single'}]:
            self.assertEqual(self.client.patch(f'/api/events/{self.event.pk}/',data,format='json').status_code,400)

    def test_finished_event_cannot_change_scoring_rules(self):
        self.meet.status='finished';self.meet.save()
        self.assertEqual(self.client.patch(f'/api/events/{self.event.pk}/',{'score_rules':{'1':100}},format='json').status_code,400)

    def test_scoring_rule_change_refreshes_results_and_totals(self):
        self.event.stage_type='single';self.event.save()
        score=Score.objects.create(registration=self.regs[0],result_numeric=10,rank=1,points=4)
        res=self.client.patch(f'/api/events/{self.event.pk}/',{'score_rules':{'1':9}},format='json')
        self.assertEqual(res.status_code,200);score.refresh_from_db();self.assertEqual(score.points,9)
        self.assertEqual(ClassPoints.objects.get(grade='',class_name=self.regs[0].student.class_name).total_points,9)

    def test_zero_point_medal_is_counted(self):
        self.event.stage_type='single';self.event.save()
        Score.objects.create(registration=self.regs[0],result_numeric=10,rank=1,points=0)
        recalculate_class_points(self.meet)
        row=ClassPoints.objects.get(grade='',class_name=self.regs[0].student.class_name)
        self.assertEqual((row.total_points,row.gold_medals),(0,1))

    def test_team_grade_uses_members_when_class_name_has_no_year(self):
        self.event.event_type='relay';self.event.save()
        team=TeamRegistration.objects.create(event=self.event,class_name='初一1班',status='approved');team.members.add(self.regs[0].student)
        TeamScore.objects.create(team_registration=team,result_numeric=10,rank=1,points=4)
        recalculate_class_points(self.meet)
        self.assertTrue(ClassPoints.objects.filter(grade='初一',class_name='初一1班').exists())

    def test_duplicate_schedule_group_is_rejected(self):
        Schedule.objects.create(event=self.event,stage='preliminary',group_number=1)
        self.assertEqual(self.client.post('/api/schedules/',{'event':self.event.pk,'stage':'preliminary','group_number':1},format='json').status_code,400)

    def test_assigned_schedule_cannot_change_stage(self):
        schedule=Schedule.objects.create(event=self.event,stage='preliminary');Registration.objects.filter(pk=self.regs[0].pk).update(schedule=schedule,lane=1)
        self.assertEqual(self.client.patch(f'/api/schedules/{schedule.pk}/',{'stage':'final'},format='json').status_code,400)

    def test_deleting_unscored_schedule_clears_lane(self):
        schedule=Schedule.objects.create(event=self.event,stage='preliminary');Registration.objects.filter(pk=self.regs[0].pk).update(schedule=schedule,lane=3)
        self.assertEqual(self.client.delete(f'/api/schedules/{schedule.pk}/').status_code,204)
        self.regs[0].refresh_from_db();self.assertIsNone(self.regs[0].lane)

    def test_scored_schedule_cannot_be_deleted(self):
        schedule=Schedule.objects.create(event=self.event,stage='preliminary');Registration.objects.filter(pk=self.regs[0].pk).update(schedule=schedule,lane=3);self.prelim()
        self.assertEqual(self.client.delete(f'/api/schedules/{schedule.pk}/').status_code,400)

    def test_meet_with_results_cannot_return_to_registration(self):
        self.prelim()
        for route in [f'/api/sports-meets/{self.meet.pk}/set_status/',f'/api/sports-meets/{self.meet.pk}/']:
            action=self.client.post if route.endswith('set_status/') else self.client.patch
            self.assertEqual(action(route,{'status':'registration'},format='json').status_code,400)

    def test_three_stage_final_requires_semifinal_advancement(self):
        self.event.stage_type='three';self.event.save();self.prelim()
        self.advance([self.regs[0].pk])
        self.assertEqual(self.client.post('/api/scores/',{'registration':self.regs[0].pk,'stage':'final','result_numeric':10},format='json').status_code,400)
        res=self.client.post('/api/scores/',{'registration':self.regs[0].pk,'stage':'semifinal','result_numeric':10},format='json')
        self.assertEqual(res.status_code,201)
        self.assertEqual(self.client.post('/api/scores/confirm_advancement/',{'event_id':self.event.pk,'stage':'semifinal','registration_ids':[self.regs[0].pk]},format='json').status_code,200)
        self.assertEqual(self.client.post('/api/scores/',{'registration':self.regs[0].pk,'stage':'final','result_numeric':10},format='json').status_code,201)

    def test_batch_cannot_bypass_final_eligibility_and_rolls_back(self):
        self.prelim();self.advance([self.regs[0].pk])
        res=self.client.post('/api/scores/batch_submit/',{'scores':[{'registration_id':reg.pk,'stage':'final','result_numeric':10} for reg in self.regs[:2]]},format='json')
        self.assertEqual(res.status_code,400);self.assertEqual(Score.objects.filter(stage='final').count(),0)

    def test_auto_top_replaces_previous_selection_and_assignments(self):
        self.prelim();self.advance([self.regs[2].pk])
        res=self.client.post('/api/scores/auto_advance_top/',{'event_id':self.event.pk,'advance_count':1},format='json')
        self.assertEqual(res.status_code,200);self.regs[2].refresh_from_db();self.assertIsNone(self.regs[2].schedule)
        self.assertTrue(Score.objects.get(registration=self.regs[0],stage='preliminary').is_advanced)

    def test_relay_groups_respect_lane_capacity(self):
        relay=Event.objects.create(sports_meet=self.meet,name='接力',event_type='relay')
        for i in range(5):TeamRegistration.objects.create(event=relay,class_name=f'{i}班',status='approved')
        self.assertEqual(self.client.post(f'/api/events/{relay.pk}/auto_assign_lanes/',{'lanes_per_group':2},format='json').status_code,200)
        self.assertEqual(Schedule.objects.filter(event=relay).count(),3)
        self.assertFalse(TeamRegistration.objects.filter(event=relay,lane__gt=2).exists())

    def test_same_source_result_patch_preserves_advancement(self):
        self.prelim();self.advance([self.regs[0].pk]);score=Score.objects.get(registration=self.regs[0],stage='preliminary')
        self.assertEqual(self.client.patch(f'/api/scores/{score.pk}/',{'result_numeric':10},format='json').status_code,200)
        score.refresh_from_db();self.assertTrue(score.is_advanced)

    def test_deleting_unscored_advancement_source_clears_assignment(self):
        self.prelim();self.advance([self.regs[0].pk]);score=Score.objects.get(registration=self.regs[0],stage='preliminary')
        self.assertEqual(self.client.delete(f'/api/scores/{score.pk}/').status_code,204)
        self.regs[0].refresh_from_db();self.assertIsNone(self.regs[0].schedule)

    def test_new_advancement_preserves_existing_lane_without_collision(self):
        self.prelim();self.advance([self.regs[0].pk]);self.advance([self.regs[0].pk,self.regs[1].pk])
        self.regs[0].refresh_from_db();self.regs[1].refresh_from_db()
        self.assertEqual(self.regs[0].lane,1);self.assertEqual(self.regs[1].lane,2)

    def test_schedule_group_must_be_positive(self):
        self.assertEqual(self.client.post('/api/schedules/',{'event':self.event.pk,'stage':'preliminary','group_number':0},format='json').status_code,400)

    def test_legacy_unqualified_final_result_is_not_ranked(self):
        from scores.views import calculate_rank_and_points
        score=Score.objects.create(registration=self.regs[0],stage='final',result_numeric=10,rank=1,points=4)
        calculate_rank_and_points(self.event,'final');score.refresh_from_db()
        self.assertIsNone(score.rank);self.assertEqual(score.points,0)

    def test_team_participants_include_schedule_group(self):
        relay=Event.objects.create(sports_meet=self.meet,name='接力',event_type='relay')
        schedule=Schedule.objects.create(event=relay,stage='final',group_number=2)
        TeamRegistration.objects.create(event=relay,class_name='1班',status='approved',schedule=schedule,lane=1)
        row=self.client.get(f'/api/events/{relay.pk}/participants/?stage=final').data[0]
        self.assertEqual((row['schedule_info']['stage'],row['schedule_info']['group_number']),(schedule.get_stage_display(),2))
