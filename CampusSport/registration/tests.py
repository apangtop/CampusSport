from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from accounts.models import User
from events.models import SportsMeet, Event, Schedule
from registration.models import Student, Registration, TeamRegistration


class RegistrationWorkflowTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user('a', role='admin')
        self.teacher = User.objects.create_user('t', role='teacher', class_name='2028级1班')
        self.meet = SportsMeet.objects.create(name='本届', status='registration', max_events_per_person=2)
        self.other_meet = SportsMeet.objects.create(name='其他届', status='registration')
        self.event = Event.objects.create(name='100米', sports_meet=self.meet, event_type='track', gender='male', max_per_class=2)
        self.other_event = Event.objects.create(name='跳远', sports_meet=self.other_meet, event_type='field')
        self.team_event = Event.objects.create(name='接力', sports_meet=self.meet, event_type='relay', team_size=2, gender='male')
        self.students = [Student.objects.create(name=str(i), gender='male', class_name=self.teacher.class_name, grade='2028级') for i in range(4)]
        self.client = APIClient(); self.client.force_authenticate(self.teacher)

    def reg(self, student=0, status='submitted', event=None):
        return Registration.objects.create(event=event or self.event, student=self.students[student], status=status)

    def team(self, status='submitted', event=None):
        reg = TeamRegistration.objects.create(event=event or self.team_event, class_name=self.teacher.class_name, status=status)
        reg.members.set(self.students[:2]); return reg

    def test_individual_create_restores_cancelled_record(self):
        reg=self.reg(status='cancelled'); reg.lane=3;reg.schedule=Schedule.objects.create(event=self.event);reg.save()
        res=self.client.post('/api/registrations/',{'event':self.event.pk,'student':self.students[0].pk},format='json')
        self.assertEqual(res.status_code,201);reg.refresh_from_db()
        self.assertEqual(Registration.objects.count(),1);self.assertEqual(reg.status,'submitted')
        self.assertIsNone(reg.lane);self.assertIsNone(reg.schedule)

    def test_bulk_restore_clears_old_assignment(self):
        reg=self.reg(status='rejected');reg.lane=4;reg.save()
        res=self.client.post('/api/registrations/bulk_register/',{'event_id':self.event.pk,'student_ids':[self.students[0].pk]},format='json')
        self.assertEqual(res.status_code,200);reg.refresh_from_db();self.assertIsNone(reg.lane)

    def test_bulk_ids_cannot_repeat(self):
        res=self.client.post('/api/registrations/bulk_register/',{'event_id':self.event.pk,'student_ids':[self.students[0].pk]*2},format='json')
        self.assertEqual(res.status_code,400);self.assertIn('不能重复',str(res.data))
        self.assertEqual(Registration.objects.count(),0)

    def test_partial_batch_only_reserves_eligible_seats(self):
        self.event.max_per_class=1;self.event.save()
        self.students[0].gender='female';self.students[0].save()
        res=self.client.post('/api/registrations/bulk_register/',{'event_id':self.event.pk,'student_ids':[s.pk for s in self.students[:2]]},format='json')
        self.assertEqual(res.status_code,200);self.assertEqual(res.data['created'],[self.students[1].name])
        self.assertTrue(res.data['errors']);self.assertEqual(Registration.objects.count(),1)

    def test_personal_limit_does_not_count_team_membership(self):
        self.meet.max_events_per_person=1;self.meet.save();self.team(status='approved')
        res=self.client.post('/api/registrations/',{'event':self.event.pk,'student':self.students[0].pk},format='json')
        self.assertEqual(res.status_code,201)

    def test_teacher_cannot_assign_lane(self):
        reg=self.reg()
        res=self.client.patch(f'/api/registrations/{reg.pk}/',{'lane':1},format='json')
        self.assertEqual(res.status_code,403);reg.refresh_from_db();self.assertIsNone(reg.lane)

    def test_admin_can_assign_lane_during_ongoing(self):
        reg=self.reg(status='approved');self.meet.status='ongoing';self.meet.save();self.client.force_authenticate(self.admin)
        res=self.client.patch(f'/api/registrations/{reg.pk}/',{'lane':2},format='json')
        self.assertEqual(res.status_code,200);reg.refresh_from_db();self.assertEqual(reg.lane,2)

    def test_team_rejection_can_be_resubmitted(self):
        reg=self.team(status='rejected')
        res=self.client.post('/api/team-registrations/',{'event':self.team_event.pk,'class_name':self.teacher.class_name,'members':[s.pk for s in self.students[:2]]},format='json')
        self.assertEqual(res.status_code,201);reg.refresh_from_db();self.assertEqual(reg.status,'submitted')
        self.assertEqual(TeamRegistration.objects.count(),1)

    def test_team_cancel_keeps_record(self):
        reg=self.team()
        self.assertEqual(self.client.post(f'/api/team-registrations/{reg.pk}/cancel/',{},format='json').status_code,200)
        self.assertTrue(TeamRegistration.objects.filter(pk=reg.pk).exists());reg.refresh_from_db();self.assertEqual(reg.status,'cancelled')

    def test_changing_approved_team_requires_new_review(self):
        reg=self.team(status='approved');reg.lane=2;reg.save()
        res=self.client.patch(f'/api/team-registrations/{reg.pk}/',{'members':[s.pk for s in self.students[1:3]]},format='json')
        self.assertEqual(res.status_code,200);reg.refresh_from_db()
        self.assertEqual(reg.status,'submitted');self.assertIsNone(reg.lane)

    def test_same_team_members_preserve_approval(self):
        reg=self.team(status='approved')
        res=self.client.patch(f'/api/team-registrations/{reg.pk}/',{'members':[s.pk for s in reversed(self.students[:2])]},format='json')
        self.assertEqual(res.status_code,200);reg.refresh_from_db();self.assertEqual(reg.status,'approved')

    def test_empty_team_with_unspecified_size_is_not_valid(self):
        self.team_event.team_size=0;self.team_event.save()
        res=self.client.post('/api/team-registrations/',{'event':self.team_event.pk,'class_name':self.teacher.class_name,'members':[]},format='json')
        self.assertEqual(res.status_code,400)

    def test_bulk_approval_requires_scope(self):
        self.reg();self.reg(student=1,event=self.other_event);self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.post('/api/registrations/approve_all/',{},format='json').status_code,400)
        self.assertEqual(Registration.objects.filter(status='approved').count(),0)

    def test_bulk_approval_is_scoped_to_current_meet(self):
        current=self.reg();other=self.reg(student=1,event=self.other_event);self.client.force_authenticate(self.admin)
        res=self.client.post('/api/registrations/approve_all/',{'sports_meet_id':self.meet.pk},format='json')
        self.assertEqual(res.status_code,200);current.refresh_from_db();other.refresh_from_db()
        self.assertEqual(current.status,'approved');self.assertEqual(other.status,'submitted')

    def test_bulk_approval_rejects_inconsistent_event_and_meet(self):
        self.reg(event=self.other_event);self.client.force_authenticate(self.admin)
        res=self.client.post('/api/registrations/approve_all/',{'sports_meet_id':self.meet.pk,'event_id':self.other_event.pk},format='json')
        self.assertEqual(res.status_code,400);self.assertEqual(Registration.objects.filter(status='approved').count(),0)

    def test_approval_revalidates_gender_and_capacity(self):
        reg=self.reg();self.event.gender='female';self.event.save();self.client.force_authenticate(self.admin)
        res=self.client.post(f'/api/registrations/{reg.pk}/approve/',{},format='json')
        self.assertEqual(res.status_code,400);reg.refresh_from_db();self.assertEqual(reg.status,'submitted')

    def test_bulk_approval_validates_each_record_and_reports_errors(self):
        valid=self.reg();invalid=self.reg(student=1);self.students[1].gender='female';self.students[1].save();self.client.force_authenticate(self.admin)
        res=self.client.post('/api/registrations/approve_all/',{'event_id':self.event.pk},format='json')
        self.assertEqual(res.status_code,200);self.assertEqual(res.data['approved'],1);self.assertTrue(res.data['errors'])
        valid.refresh_from_db();invalid.refresh_from_db();self.assertEqual(valid.status,'approved');self.assertEqual(invalid.status,'submitted')

    def test_cancelled_record_cannot_be_rejected(self):
        reg=self.reg(status='cancelled');self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.post(f'/api/registrations/{reg.pk}/reject/',{},format='json').status_code,400)
        reg.refresh_from_db();self.assertEqual(reg.status,'cancelled')

    def test_teacher_deadline_boundary_is_closed(self):
        from unittest.mock import patch
        now=timezone.now();self.meet.registration_deadline=now;self.meet.save()
        with patch('registration.validation.timezone.now',return_value=now):
            res=self.client.post('/api/registrations/',{'event':self.event.pk,'student':self.students[0].pk},format='json')
        self.assertEqual(res.status_code,400)

    def test_student_partial_update_preserves_class(self):
        self.assertEqual(self.client.patch(f'/api/students/{self.students[0].pk}/',{'name':'更新姓名'},format='json').status_code,200)

    def test_active_registration_blocks_incompatible_student_edit(self):
        self.reg(status='approved')
        self.assertEqual(self.client.patch(f'/api/students/{self.students[0].pk}/',{'gender':'female','class_name':self.teacher.class_name},format='json').status_code,400)
        self.students[0].refresh_from_db();self.assertEqual(self.students[0].gender,'male')

    def test_team_bulk_approval_respects_scope(self):
        reg=self.team();other=self.team(event=self.other_event);self.client.force_authenticate(self.admin)
        res=self.client.post('/api/team-registrations/approve_all/',{'sports_meet_id':self.meet.pk},format='json')
        self.assertEqual(res.status_code,200);reg.refresh_from_db();other.refresh_from_db();self.assertEqual(reg.status,'approved');self.assertEqual(other.status,'submitted')


    def test_excel_import_cannot_invalidate_active_registration(self):
        import io, openpyxl
        self.reg(status='approved')
        wb=openpyxl.Workbook();wb.active.append(['姓名','性别','学号','年级','班级'])
        wb.active.append([self.students[0].name,'女','','2028级',self.teacher.class_name])
        buf=io.BytesIO();wb.save(buf);buf.seek(0);buf.name='students.xlsx'
        res=self.client.post('/api/students/import_excel/',{'file':buf},format='multipart')
        self.assertEqual(res.status_code,200);self.assertTrue(res.data['errors'])
        self.students[0].refresh_from_db();self.assertEqual(self.students[0].gender,'male')

    def test_team_member_cannot_be_deleted_without_handling_registration(self):
        reg=self.team(status='approved')
        self.assertEqual(self.client.delete(f'/api/students/{self.students[0].pk}/').status_code,400)
        self.assertEqual(reg.members.count(),2)

    def test_cancelled_team_can_be_resubmitted(self):
        reg=self.team();self.client.post(f'/api/team-registrations/{reg.pk}/cancel/',{},format='json')
        res=self.client.post('/api/team-registrations/',{'event':self.team_event.pk,'class_name':self.teacher.class_name,'members':[s.pk for s in self.students[:2]]},format='json')
        self.assertEqual(res.status_code,201);self.assertEqual(TeamRegistration.objects.count(),1)
        reg.refresh_from_db();self.assertEqual(reg.status,'submitted')

    def test_unapproved_registration_cannot_be_scheduled(self):
        reg=self.reg();self.client.force_authenticate(self.admin)
        res=self.client.patch(f'/api/registrations/{reg.pk}/',{'lane':1},format='json')
        self.assertEqual(res.status_code,400)

    def test_duplicate_lanes_in_same_schedule_are_rejected(self):
        schedule=Schedule.objects.create(event=self.event)
        a=self.reg(status='approved');a.schedule=schedule;a.lane=1;a.save()
        b=self.reg(student=1,status='approved');b.schedule=schedule;b.save()
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.patch(f'/api/registrations/{b.pk}/',{'lane':1},format='json').status_code,400)
        b.refresh_from_db();self.assertIsNone(b.lane)

    def test_same_lane_is_allowed_in_different_groups(self):
        first=Schedule.objects.create(event=self.event,group_number=1)
        second=Schedule.objects.create(event=self.event,group_number=2)
        a=self.reg(status='approved');a.schedule=first;a.lane=1;a.save()
        b=self.reg(student=1,status='approved');b.schedule=second;b.save()
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.patch(f'/api/registrations/{b.pk}/',{'lane':1},format='json').status_code,200)

    def test_filtered_batch_approval_does_not_touch_other_classes(self):
        a=self.reg();self.students[1].class_name='2028级2班';self.students[1].save();b=self.reg(student=1)
        self.client.force_authenticate(self.admin)
        res=self.client.post('/api/registrations/approve_all/',{'sports_meet_id':self.meet.pk,'class_name':self.teacher.class_name},format='json')
        self.assertEqual(res.status_code,200);self.assertEqual(res.data['approved'],1)
        a.refresh_from_db();b.refresh_from_db();self.assertEqual(a.status,'approved');self.assertEqual(b.status,'submitted')

    def test_live_duplicate_submission_does_not_change_approval(self):
        reg=self.reg(status='approved')
        res=self.client.post('/api/registrations/',{'event':self.event.pk,'student':self.students[0].pk},format='json')
        self.assertEqual(res.status_code,400);reg.refresh_from_db();self.assertEqual(reg.status,'approved')

    def test_approval_rejects_overfull_legacy_registration(self):
        a=self.reg();self.reg(student=1,status='approved');self.event.max_per_class=1;self.event.save();self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.post(f'/api/registrations/{a.pk}/approve/',{},format='json').status_code,400)
        a.refresh_from_db();self.assertEqual(a.status,'submitted')

    def test_team_approval_rechecks_member_count(self):
        reg=self.team();reg.members.remove(self.students[1]);self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.post(f'/api/team-registrations/{reg.pk}/approve/',{},format='json').status_code,400)
        reg.refresh_from_db();self.assertEqual(reg.status,'submitted')


    def test_cancelling_individual_releases_person_and_class_quota(self):
        self.meet.max_events_per_person=1;self.meet.save();self.event.max_per_class=1;self.event.save()
        reg=self.reg(status='approved')
        self.assertEqual(self.client.post(f'/api/registrations/{reg.pk}/cancel/',{},format='json').status_code,200)
        res=self.client.post('/api/registrations/',{'event':self.event.pk,'student':self.students[1].pk},format='json')
        self.assertEqual(res.status_code,201)

    def test_cancel_after_deadline_keeps_registration(self):
        reg=self.reg();self.meet.registration_deadline=timezone.now()-timedelta(seconds=1);self.meet.save()
        self.assertEqual(self.client.post(f'/api/registrations/{reg.pk}/cancel/',{},format='json').status_code,400)
        reg.refresh_from_db();self.assertEqual(reg.status,'submitted')

    def test_admin_can_review_after_deadline_but_not_when_ongoing(self):
        reg=self.reg();self.meet.registration_deadline=timezone.now()-timedelta(seconds=1);self.meet.save();self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.post(f'/api/registrations/{reg.pk}/approve/',{},format='json').status_code,200)
        self.meet.status='ongoing';self.meet.save()
        self.assertEqual(self.client.post(f'/api/registrations/{reg.pk}/cancel/',{},format='json').status_code,400)
        reg.refresh_from_db();self.assertEqual(reg.status,'approved')

    def test_team_member_gender_edit_is_blocked(self):
        self.team(status='approved')
        self.assertEqual(self.client.patch(f'/api/students/{self.students[0].pk}/',{'gender':'female'},format='json').status_code,400)

    def test_rejected_and_cancelled_records_do_not_use_quota(self):
        self.meet.max_events_per_person=1;self.meet.save()
        other=Event.objects.create(name='200米',sports_meet=self.meet,event_type='track',max_per_class=1)
        self.reg(status='rejected')
        self.assertEqual(self.client.post('/api/registrations/',{'event':other.pk,'student':self.students[0].pk},format='json').status_code,201)

    def test_team_members_cannot_repeat(self):
        res=self.client.post('/api/team-registrations/',{'event':self.team_event.pk,'class_name':self.teacher.class_name,'members':[self.students[0].pk]*2},format='json')
        self.assertEqual(res.status_code,400);self.assertEqual(TeamRegistration.objects.count(),0)

    def test_team_members_cannot_be_replaced_after_deadline(self):
        reg=self.team(status='approved');self.meet.registration_deadline=timezone.now()-timedelta(seconds=1);self.meet.save()
        self.assertEqual(self.client.patch(f'/api/team-registrations/{reg.pk}/',{'members':[s.pk for s in self.students[1:3]]},format='json').status_code,400)
        reg.refresh_from_db();self.assertEqual(reg.status,'approved');self.assertEqual(list(reg.members.order_by('pk').values_list('pk',flat=True)),[s.pk for s in self.students[:2]])

    def test_person_limit_is_separate_for_each_meet(self):
        self.meet.max_events_per_person=1;self.meet.save();self.reg(event=self.other_event,status='approved')
        self.assertEqual(self.client.post('/api/registrations/',{'event':self.event.pk,'student':self.students[0].pk},format='json').status_code,201)
