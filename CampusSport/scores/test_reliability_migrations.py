from django.test import TransactionTestCase
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


class ReliabilityMigrationTests(TransactionTestCase):
    migrate_from=[('events','0004_event_grade'),('registration','0003_team_cancelled_status'),('scores','0002_auto_20260511_1730')]
    migrate_to=[('events','0005_schedule_event_stage_group_unique'),('registration','0004_auto_20261006_2112'),('scores','0003_auto_20261006_2112')]

    def setUp(self):
        executor=MigrationExecutor(connection);executor.migrate(self.migrate_from)
        self.apps=executor.loader.project_state(self.migrate_from).apps
        self.extra_cleanup=[]

    def tearDown(self):
        for model,pk in self.extra_cleanup:model.objects.filter(pk=pk).delete()
        executor=MigrationExecutor(connection);executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def migrate(self):
        executor=MigrationExecutor(connection);executor.migrate(self.migrate_to)
        return executor.loader.project_state(self.migrate_to).apps

    def make_event(self):
        meet=self.apps.get_model('events','SportsMeet').objects.create(name='已有数据')
        event=self.apps.get_model('events','Event').objects.create(sports_meet=meet,name='100米',event_type='track')
        return event

    def test_existing_blank_ids_preserved_as_null_without_merging(self):
        student=self.apps.get_model('registration','Student')
        for name in ['甲','乙']:student.objects.create(name=name,class_name='1班',gender='male',student_id='')
        apps=self.migrate();current=apps.get_model('registration','Student')
        self.assertEqual(current.objects.count(),2);self.assertEqual(current.objects.filter(student_id__isnull=True).count(),2)

    def test_duplicate_identifiers_abort_and_preserve_rows(self):
        student=self.apps.get_model('registration','Student')
        student.objects.create(name='甲',class_name='1班',gender='male',student_id='100')
        duplicate=student.objects.create(name='乙',class_name='1班',gender='male',student_id='100');self.extra_cleanup.append((student,duplicate.pk))
        with self.assertRaisesRegex(RuntimeError,'重复学号'):self.migrate()
        self.assertEqual(student.objects.filter(student_id='100').count(),2)

    def test_duplicate_schedules_abort_without_deleting(self):
        event=self.make_event();model=self.apps.get_model('events','Schedule')
        model.objects.create(event=event,stage='final',group_number=1)
        duplicate=model.objects.create(event=event,stage='final',group_number=1);self.extra_cleanup.append((model,duplicate.pk))
        with self.assertRaisesRegex(RuntimeError,'重复赛程'):self.migrate()
        self.assertEqual(model.objects.count(),2)

    def test_existing_current_stage_is_backfilled_but_unknown_past_group_is_not_invented(self):
        event=self.make_event();schedule=self.apps.get_model('events','Schedule').objects.create(event=event,stage='final',group_number=2)
        student=self.apps.get_model('registration','Student').objects.create(name='甲',class_name='1班',gender='male')
        reg=self.apps.get_model('registration','Registration').objects.create(event=event,student=student,schedule=schedule,lane=3)
        model=self.apps.get_model('scores','Score');final=model.objects.create(registration=reg,stage='final',result_numeric=10)
        preliminary=model.objects.create(registration=reg,stage='preliminary',result_numeric=11)
        apps=self.migrate();current=apps.get_model('scores','Score')
        self.assertEqual((current.objects.get(pk=final.pk).schedule_id,current.objects.get(pk=final.pk).lane),(schedule.pk,3))
        self.assertIsNone(current.objects.get(pk=preliminary.pk).schedule_id)
