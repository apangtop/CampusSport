from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.db.models import Min
from .models import SportsMeet, Event
from scores.models import Score, ClassPoints
from registration.models import Student


class HistoryMeetListView(APIView):
    """历届运动会列表"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        meets = SportsMeet.objects.filter(status='finished').order_by('-session')
        data = [
            {
                'id': m.id,
                'name': m.name,
                'session': m.session,
                'school': m.school,
                'start_date': str(m.start_date) if m.start_date else None,
                'end_date': str(m.end_date) if m.end_date else None,
                'event_count': m.events.count(),
            }
            for m in meets
        ]
        return Response(data)


class HistoryPointsView(APIView):
    """历届班级积分榜"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        meet_id = request.query_params.get('sports_meet')
        qs = ClassPoints.objects.all()
        if meet_id:
            qs = qs.filter(sports_meet_id=meet_id)
        data = [
            {
                'meet_name': cp.sports_meet.name,
                'session': cp.sports_meet.session,
                'class_name': cp.class_name,
                'total_points': cp.total_points,
                'gold_medals': cp.gold_medals,
                'silver_medals': cp.silver_medals,
                'bronze_medals': cp.bronze_medals,
                'rank': cp.rank,
            }
            for cp in qs.select_related('sports_meet').order_by('sports_meet__session', 'rank')
        ]
        return Response(data)


class HistoryEventBestView(APIView):
    """项目历史最佳成绩"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        event_name = request.query_params.get('event_name')
        if not event_name:
            # 返回所有项目名称列表
            names = Event.objects.values_list('name', flat=True).distinct()
            return Response(list(names))

        scores = Score.objects.filter(
            registration__event__name=event_name,
            stage='final',
            rank=1,
            result_numeric__isnull=False
        ).select_related(
            'registration__student',
            'registration__event__sports_meet'
        ).order_by('registration__event__sports_meet__session')

        data = []
        for s in scores:
            meet = s.registration.event.sports_meet
            data.append({
                'session': meet.session,
                'meet_name': meet.name,
                'start_date': str(meet.start_date) if meet.start_date else None,
                'student_name': s.registration.student.name,
                'class_name': s.registration.student.class_name,
                'result': s.result,
                'result_numeric': s.result_numeric,
            })
        return Response(data)


class StudentHistoryView(APIView):
    """学生历届参赛记录"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        student_name = request.query_params.get('name')
        class_name = request.query_params.get('class_name')

        qs = Score.objects.all()
        if student_name:
            qs = qs.filter(registration__student__name__icontains=student_name)
        if class_name:
            qs = qs.filter(registration__student__class_name=class_name)

        qs = qs.select_related(
            'registration__student',
            'registration__event',
            'registration__event__sports_meet'
        ).filter(stage='final').order_by(
            'registration__event__sports_meet__session'
        )

        data = []
        for s in qs:
            meet = s.registration.event.sports_meet
            student = s.registration.student
            data.append({
                'session': meet.session,
                'meet_name': meet.name,
                'student_name': student.name,
                'class_name': student.class_name,
                'event_name': s.registration.event.name,
                'result': s.result,
                'rank': s.rank,
                'points': s.points,
            })
        return Response(data)
