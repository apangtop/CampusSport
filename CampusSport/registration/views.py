from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
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
            qs = qs.filter(class_name=class_name)
        gender = self.request.query_params.get('gender')
        if gender:
            qs = qs.filter(gender=gender)
        return qs

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminOrTeacher()]
        return [permissions.IsAuthenticated()]

    @action(detail=False, methods=['post'], permission_classes=[IsAdminOrTeacher])
    def import_excel(self, request):
        """从 Excel 批量导入学生"""
        file = request.FILES.get('file')
        if not file:
            return Response({'detail': '请上传Excel文件'}, status=status.HTTP_400_BAD_REQUEST)
        class_name = request.data.get('class_name') or request.user.class_name
        if not class_name:
            return Response({'detail': '请指定班级'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            wb = openpyxl.load_workbook(file)
            ws = wb.active
        except Exception:
            return Response({'detail': '文件格式错误，请上传xlsx文件'}, status=status.HTTP_400_BAD_REQUEST)

        created, updated, errors = [], [], []
        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
            if not row or not row[0]:
                continue
            name = str(row[0]).strip()
            gender_raw = str(row[1]).strip() if len(row) > 1 and row[1] else '男'
            student_id = str(row[2]).strip() if len(row) > 2 and row[2] else ''
            grade = str(row[3]).strip() if len(row) > 3 and row[3] else ''
            gender = 'male' if gender_raw in ['男', 'male', 'M', 'm'] else 'female'

            if not name:
                errors.append(f'第{row_idx}行：姓名为空')
                continue

            obj, is_created = Student.objects.update_or_create(
                name=name, class_name=class_name,
                defaults={'gender': gender, 'student_id': student_id, 'grade': grade}
            )
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
        headers = ['姓名*', '性别(男/女)*', '学号', '年级']
        for col, h in enumerate(headers, 1):
            ws.cell(row=1, column=col, value=h)
        # 示例数据
        ws.append(['张三', '男', '2024001', '初一'])
        ws.append(['李四', '女', '2024002', '初一'])

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
        students_data = request.data if isinstance(request.data, list) else request.data.get('students', [])
        if not students_data:
            return Response({'detail': '请提供学生列表'}, status=status.HTTP_400_BAD_REQUEST)

        class_name = request.data.get('class_name') if isinstance(request.data, dict) else ''
        created, errors = [], []
        for item in students_data:
            name = item.get('name', '').strip()
            if not name:
                errors.append('姓名为空')
                continue
            item_class = item.get('class_name', class_name) or (request.user.class_name if request.user.role == 'teacher' else '')
            if not item_class:
                errors.append(f'{name}: 缺少班级信息')
                continue
            gender_raw = item.get('gender', '男')
            gender = 'male' if str(gender_raw) in ['男', 'male', 'M', 'm'] else 'female'
            obj, is_new = Student.objects.get_or_create(
                name=name, class_name=item_class,
                defaults={
                    'gender': gender,
                    'student_id': item.get('student_id', ''),
                    'grade': item.get('grade', ''),
                }
            )
            if is_new:
                created.append(name)
        return Response({'created': len(created), 'errors': errors, 'detail': f'新增 {len(created)} 名学生'})


class RegistrationViewSet(viewsets.ModelViewSet):
    queryset = Registration.objects.select_related('student', 'event', 'submitted_by', 'schedule').all()
    permission_classes = [permissions.IsAuthenticated]

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

        event_id = self.request.query_params.get('event')
        if event_id:
            qs = qs.filter(event_id=event_id)
        class_name = self.request.query_params.get('class_name')
        if class_name:
            qs = qs.filter(student__class_name=class_name)
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        meet_id = self.request.query_params.get('sports_meet')
        if meet_id:
            qs = qs.filter(event__sports_meet_id=meet_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(submitted_by=self.request.user)

    def _check_teacher_permission(self, registration):
        user = self.request.user
        if user.role == 'teacher' and registration.student.class_name != user.class_name:
            return False
        return True

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not self._check_teacher_permission(instance):
            return Response({'detail': '只能操作本班学生的报名'}, status=status.HTTP_403_FORBIDDEN)
        if instance.event.sports_meet.status not in ['registration'] and request.user.role != 'admin':
            return Response({'detail': '报名截止后不可修改'}, status=status.HTTP_400_BAD_REQUEST)
        return super().update(request, *args, **kwargs)

    @action(detail=False, methods=['post'], permission_classes=[IsAdminOrTeacher])
    def bulk_register(self, request):
        """批量报名"""
        serializer = BulkRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        event_id = serializer.validated_data['event_id']
        student_ids = serializer.validated_data['student_ids']

        try:
            event = Event.objects.select_related('sports_meet').get(id=event_id)
        except Event.DoesNotExist:
            return Response({'detail': '项目不存在'}, status=status.HTTP_404_NOT_FOUND)

        meet = event.sports_meet

        # 检查运动会状态和报名截止时间
        if meet.status != 'registration' and request.user.role != 'admin':
            return Response({'detail': '当前不在报名阶段'}, status=status.HTTP_400_BAD_REQUEST)
        if meet.registration_deadline and timezone.now() > meet.registration_deadline and request.user.role != 'admin':
            return Response({'detail': '报名已截止'}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        if user.role == 'teacher':
            students = Student.objects.filter(id__in=student_ids, class_name=user.class_name)
            if students.count() != len(student_ids):
                return Response({'detail': '只能为本班学生报名'}, status=status.HTTP_400_BAD_REQUEST)

            # 检查每班报名上限
            current_count = Registration.objects.filter(
                event=event,
                student__class_name=user.class_name,
                status__in=['submitted', 'approved']
            ).count()
            if current_count + len(student_ids) > event.max_per_class:
                return Response({'detail': f'超出每班报名上限({event.max_per_class}人)'}, status=status.HTTP_400_BAD_REQUEST)

        created = []
        errors = []
        with transaction.atomic():
            for student_id in student_ids:
                try:
                    student = Student.objects.get(id=student_id)

                    # 检查性别匹配
                    if event.gender != 'mixed' and student.gender != event.gender:
                        errors.append(f'{student.name} 性别不符（项目要求{event.get_gender_display()}）')
                        continue

                    # 检查每人报名项目数：以 event.max_per_person 为准，meet 上限兜底
                    per_event_cap = event.max_per_person or meet.max_events_per_person
                    person_count = Registration.objects.filter(
                        student=student,
                        event__sports_meet=meet,
                        status__in=['submitted', 'approved']
                    ).count()
                    if person_count >= per_event_cap:
                        errors.append(f'{student.name} 已达到报名项目上限（{per_event_cap}个）')
                        continue
                    reg, created_flag = Registration.objects.get_or_create(
                        event=event, student=student,
                        defaults={'submitted_by': user, 'status': 'submitted'}
                    )
                    if created_flag:
                        created.append(student.name)
                except Student.DoesNotExist:
                    errors.append(f'学生ID {student_id} 不存在')

        return Response({'created': created, 'errors': errors})

    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def approve(self, request, pk=None):
        reg = self.get_object()
        reg.status = 'approved'
        reg.save()
        return Response({'detail': '已审核通过'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def reject(self, request, pk=None):
        reg = self.get_object()
        reg.status = 'rejected'
        reg.save()
        return Response({'detail': '已拒绝'})

    @action(detail=False, methods=['post'], permission_classes=[IsAdmin])
    def approve_all(self, request):
        """一键审核所有提交的报名"""
        event_id = request.data.get('event_id')
        qs = Registration.objects.filter(status='submitted')
        if event_id:
            qs = qs.filter(event_id=event_id)
        count = qs.update(status='approved')
        return Response({'detail': f'已审核 {count} 条报名'})


class TeamRegistrationViewSet(viewsets.ModelViewSet):
    queryset = TeamRegistration.objects.prefetch_related('members').all()
    serializer_class = TeamRegistrationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.role == 'teacher':
            qs = qs.filter(class_name=user.class_name)
        elif user.role == 'referee':
            qs = qs.filter(event__referee=user)
        event_id = self.request.query_params.get('event')
        if event_id:
            qs = qs.filter(event_id=event_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(submitted_by=self.request.user)
