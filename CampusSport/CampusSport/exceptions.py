from django.db.models.deletion import ProtectedError
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.response import Response


def exception_handler(exc, context):
    if isinstance(exc, ProtectedError):
        return Response({'detail': '该记录已有项目或报名关联，无法删除'}, status=409)
    return drf_exception_handler(exc, context)
