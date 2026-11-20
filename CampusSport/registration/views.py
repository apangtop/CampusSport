from CampusSport.input_validation import object_data, query_id
from rest_framework import serializers
from rest_framework import viewsets, status, permissions
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.http import HttpResponse
import openpyxl
import io
from .models import Student, Registration, TeamRegistration
from .serializers import (
    StudentSerializer, RegistrationSerializer,
    RegistrationDetailSerializer, TeamRegistrationSerializer,
    BulkRegistrationSerializer
)
from events.models import Event, SportsMeet
from .services import submit, change_status, approve_batch, lock_event, lock_record
from .validation import check_registration_open, validate_individual, ACTIVE_STATUSES


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'


class IsAdminOrTeacher(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['admin', 'teacher']


class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.role == 'teacher':
            qs = qs.filter(class_name=user.class_name)
        class_name = self.request.query_params.get('class_name')
        if class_name:
            from accounts.school import filter_class_or_grade
            qs = filter_class_or_grade(qs, class_name, 'class_name')
        name = self.request.query_params.get('name')
        if name:
            qs = qs.filter(name__icontains=name)
        gender = self.request.query_params.get('gender')
        if gender:
            qs = qs.filter(gender=gender)
        grade = self.request.query_params.get('grade')
        if grade:
            qs = qs.filter(grade=grade)
        return qs

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminOrTeacher()]
        return super().get_permissions()

    def perform_create(self, serializer):
        user = self.request.user
        if user.role == 'teacher':
            class_name = serializer.validated_data.get('class_name', getattr(serializer.instance, 'class_name', ''))
            if class_name != user.class_name:
                raise PermissionDenied('只能添加本班学生')
        serializer.validate(serializer.validated_data)
        from django.db import IntegrityError
        try:
            with transaction.atomic():
                serializer.save()
        except IntegrityError:
            raise ValidationError('学生学号已存在，请刷新后重试')

    @transaction.atomic
    def perform_update(self, serializer):
        serializer.instance = get_object_or_404(Student.objects.select_for_update(),pk=serializer.instance.pk)
        serializer.validate(serializer.validated_data)
        self.perform_create(serializer)

    @transaction.atomic
    def perform_destroy(self, instance):
        instance = get_object_or_404(Student.objects.select_for_update(),pk=instance.pk)
        if instance.team_registrations.filter(status__in=ACTIVE_STATUSES).exists():
            raise ValidationError('学生仍属于有效团体报名，请先调整队员或取消报名')
        instance.delete()

    @action(detail=False, methods=['post'], permission_classes=[IsAdminOrTeacher])
    def import_excel(self, request):
        """从 Excel 批量导入学生"""
        file = request.FILES.get('file')
        if not file:
            return Response({'detail': '请上传Excel文件'}, status=status.HTTP_400_BAD_REQUEST)
        default_class = object_data(request).get('class_name') or request.user.class_name or ''
        try:
            wb = openpyxl.load_workbook(file)
            ws = wb.active
        except Exception:
            return Response({'detail': '文件格式错误，请上传xlsx文件'}, status=status.HTTP_400_BAD_REQUEST)

        def cell(row, idx, default=''):
            """安全读取单元格，None → 空字符串"""
            v = row[idx] if len(row) > idx else None
            return str(v).strip() if v is not None else default

        created, updated, errors = [], [], []
        import re
        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
            if not row or not row[0]:
                continue
            name = cell(row, 0)
            if not name:
                errors.append(f'第{row_idx}行：姓名为空')
                continue
            gender_raw = cell(row, 1, '男')
            student_id = cell(row, 2)
            grade = cell(row, 3)
            row_class = cell(row, 4)
            if gender_raw not in ['男', 'male', 'M', 'm', '女', 'female', 'F', 'f']:
                errors.append(f'第{row_idx}行：性别无效')
                continue
            gender = 'male' if gender_raw in ['男', 'male', 'M', 'm'] else 'female'

            # 如果 Excel 行中没指定班级，使用请求中的默认班级
            student_class = row_class or default_class
            if not student_class:
                errors.append(f'第{row_idx}行：未指定班级')
                continue

            if request.user.role == 'teacher' and student_class != request.user.class_name:
                errors.append(f'第{row_idx}行：只能导入本班学生')
                continue

            if not grade:
                from accounts.school import class_grade
                grade = class_grade(student_class)

            from .services import import_student
            lookup = {'student_id': student_id, 'class_name': student_class} if student_id else {'name': name, 'class_name': student_class}
            try:
                obj, is_created = import_student(lookup, {'name': name, 'gender': gender,
                    'student_id': student_id, 'grade': grade}, request)
            except ValidationError as exc:
                errors.append(f'第{row_idx}行：{exc.detail}')
                continue
            (created if is_created else updated).append(name)

        return Response({
            'created': len(created),
            'updated': len(updated),
            'errors': errors,
            'detail': f'导入完成：新增{len(created)}人，更新{len(updated)}人'
        })

    @action(detail=False, methods=['get'], permission_classes=[IsAdminOrTeacher])
    def export_template(self, request):
        """下载学生导入模板"""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = '学生名单'
        headers = ['姓名', '性别(男/女)', '学号', '年级', '班级']
        for col, h in enumerate(headers, 1):
            ws.cell(row=1, column=col, value=h)
        # Templates are blank so example pupils cannot accidentally become real records.
        from accounts.school import profile, class_grade
        sample_class = request.user.class_name if request.user.role == 'teacher' else ''
        if not sample_class and profile().classes:
            sample_class = profile().classes[0]['name']
        ws.append(['', '', '', class_grade(sample_class), sample_class])

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="student_template.xlsx"'
        return response

    @action(detail=False, methods=['post'], permission_classes=[IsAdminOrTeacher])
    def bulk(self, request):
        """批量创建学生"""
        if not isinstance(request.data, (list,dict)):
            raise ValidationError('请提供学生列表')
        students_data = request.data if isinstance(request.data,list) else object_data(request).get('students',[])
        if not isinstance(students_data,list) or not 1 <= len(students_data) <= 2000:
            raise ValidationError('请提供1到2000条学生数据')
        default_class = object_data(request).get('class_name') if isinstance(request.data,dict) else ''
        if request.user.role == 'teacher':
            default_class = default_class or request.user.class_name
        from .services import create_student_once
        created, errors, unchanged = [], [], 0
        for index,item in enumerate(students_data,1):
            if not isinstance(item,dict):
                errors.append(f'第{index}条：学生资料必须为对象')
                continue
            data=dict(item)
            data['class_name']=data.get('class_name') or default_class
            gender=data.get('gender','男')
            gender_map={'男':'male','male':'male','M':'male','m':'male','女':'female','female':'female','F':'female','f':'female'}
            data['gender']=gender_map.get(str(gender),gender)
            try:
                obj,is_new=create_student_once(data,request)
            except (ValidationError,PermissionDenied) as exc:
                errors.append(f'第{index}条：{exc.detail}')
                continue
            if is_new:created.append(obj.name)
            else:unchanged+=1
        return Response({'created':len(created),'unchanged':unchanged,'errors':errors,'detail':f'新增 {len(created)} 名学生'})



class RegistrationViewSet(viewsets.ModelViewSet):
    queryset = Registration.objects.select_related('student', 'event', 'submitted_by', 'schedule').all()
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action == 'destroy':
            return [IsAdmin()]
        if self.action in ['create', 'update', 'partial_update']:
            return [IsAdminOrTeacher()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return RegistrationDetailSerializer
        return RegistrationSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.role == 'teacher':
            qs = qs.filter(student__class_name=user.class_name)
        elif user.role == 'referee':
            qs = qs.filter(event__referee=user)

        event_id = query_id(self.request.query_params, 'event')
        if event_id:
            qs = qs.filter(event_id=event_id)
        class_name = self.request.query_params.get('class_name')
        if class_name:
            from accounts.school import filter_class_or_grade
            qs = filter_class_or_grade(qs, class_name, 'student__class_name')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        meet_id = query_id(self.request.query_params, 'sports_meet')
        if meet_id:
            qs = qs.filter(event__sports_meet_id=meet_id)
        event_type = self.request.query_params.get('type')
        if event_type:
            qs = qs.filter(event__event_type=event_type)
        return qs

    def perform_create(self, serializer):
        submit(serializer, self.request.user)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        initial = self.get_object()
        record = lock_record(Registration, initial.pk)
        serializer = self.get_serializer(record, data=request.data, partial=kwargs.pop('partial', False))
        serializer.is_valid(raise_exception=True)
        if isinstance(record, TeamRegistration) and 'members' in serializer.validated_data:
            selected = serializer.validated_data['members']
            ids = {m.pk for m in selected}
            all_ids = ids | set(record.members.values_list('pk', flat=True))
            locked = list(Student.objects.select_for_update().filter(pk__in=all_ids).order_by('pk'))
            members = [m for m in locked if m.pk in ids]
            if len(members) != len(selected):
                raise ValidationError('队员数据已变化，请刷新重试')
            serializer.validated_data['members'] = members
            serializer.validate(serializer.validated_data)
        serializer.save()
        return Response(serializer.data)

    @transaction.atomic
    def perform_destroy(self, instance):
        record = lock_record(Registration, instance.pk)
        check_registration_open(record.event, self.request.user)
        record.delete()

    @action(detail=False, methods=['post'], permission_classes=[IsAdminOrTeacher])
    @transaction.atomic
    def bulk_register(self, request):
        serializer = BulkRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = lock_event(serializer.validated_data['event_id'])
        check_registration_open(event, request.user)
        student_ids = serializer.validated_data['student_ids']
        students = {s.pk: s for s in Student.objects.select_for_update().filter(pk__in=student_ids).order_by('pk')}
        if request.user.role == 'teacher' and any(s.class_name != request.user.class_name for s in students.values()):
            raise PermissionDenied('只能为本班学生报名')
        created, errors, unchanged = [], [], []
        for student_id in student_ids:
            student = students.get(student_id)
            if not student:
                errors.append(f'学生ID {student_id} 不存在')
                continue
            existing = Registration.objects.filter(event=event, student=student).first()
            if existing and existing.status in ACTIVE_STATUSES:
                unchanged.append(student.name)
                continue
            try:
                validate_individual(event, student, request.user, existing)
            except (ValidationError, PermissionDenied) as exc:
                errors.append(f'{student.name}: {exc.detail}')
                continue
            if existing:
                existing.status = 'submitted'
                existing.submitted_by = request.user
                existing.schedule = None
                existing.lane = None
                existing.save()
            else:
                Registration.objects.create(event=event, student=student, submitted_by=request.user)
            created.append(student.name)
        return Response({'created': created, 'errors': errors, 'unchanged': unchanged},
                        status=400 if errors and not created and not unchanged else 200)

    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def approve(self, request, pk=None):
        record = self.get_object()
        change_status(Registration, record.pk, 'approved', request.user)
        return Response({'detail': '已审核通过'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def reject(self, request, pk=None):
        record = self.get_object()
        change_status(Registration, record.pk, 'rejected', request.user)
        return Response({'detail': '已拒绝'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrTeacher])
    def cancel(self, request, pk=None):
        record = self.get_object()
        change_status(Registration, record.pk, 'cancelled', request.user)
        return Response({'detail': '已取消报名'})

    @action(detail=False, methods=['post'], permission_classes=[IsAdmin])
    def approve_all(self, request):
        return Response(approve_batch(Registration, request.data, request.user))


class TeamRegistrationViewSet(viewsets.ModelViewSet):
    queryset = TeamRegistration.objects.prefetch_related('members').all()
    serializer_class = TeamRegistrationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update']:
            return [IsAdminOrTeacher()]
        if self.action == 'destroy':
            return [IsAdmin()]
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.role == 'teacher':
            qs = qs.filter(class_name=user.class_name)
        elif user.role == 'referee':
            qs = qs.filter(event__referee=user)
        event_id = query_id(self.request.query_params, 'event')
        if event_id:
            qs = qs.filter(event_id=event_id)
        class_name = self.request.query_params.get('class_name')
        if class_name:
            from accounts.school import filter_class_or_grade
            qs = filter_class_or_grade(qs, class_name, 'class_name')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        meet_id = query_id(self.request.query_params, 'sports_meet')
        if meet_id:
            qs = qs.filter(event__sports_meet_id=meet_id)
        return qs

    def perform_create(self, serializer):
        submit(serializer, self.request.user)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        initial = self.get_object()
        record = lock_record(TeamRegistration, initial.pk)
        serializer = self.get_serializer(record, data=request.data, partial=kwargs.pop('partial', False))
        serializer.is_valid(raise_exception=True)
        if isinstance(record, TeamRegistration) and 'members' in serializer.validated_data:
            selected = serializer.validated_data['members']
            ids = {m.pk for m in selected}
            all_ids = ids | set(record.members.values_list('pk', flat=True))
            locked = list(Student.objects.select_for_update().filter(pk__in=all_ids).order_by('pk'))
            members = [m for m in locked if m.pk in ids]
            if len(members) != len(selected):
                raise ValidationError('队员数据已变化，请刷新重试')
            serializer.validated_data['members'] = members
            serializer.validate(serializer.validated_data)
        serializer.save()
        return Response(serializer.data)

    @transaction.atomic
    def perform_destroy(self, instance):
        record = lock_record(TeamRegistration, instance.pk)
        check_registration_open(record.event, self.request.user)
        record.delete()

    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def approve(self, request, pk=None):
        record = self.get_object()
        change_status(TeamRegistration, record.pk, 'approved', request.user)
        return Response({'detail': '已审核通过'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def reject(self, request, pk=None):
        record = self.get_object()
        change_status(TeamRegistration, record.pk, 'rejected', request.user)
        return Response({'detail': '已拒绝'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrTeacher])
    def cancel(self, request, pk=None):
        record = self.get_object()
        change_status(TeamRegistration, record.pk, 'cancelled', request.user)
        return Response({'detail': '已取消报名'})

    @action(detail=False, methods=['post'], permission_classes=[IsAdmin])
    def approve_all(self, request):
        return Response(approve_batch(TeamRegistration, request.data, request.user))
