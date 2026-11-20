from rest_framework import serializers
from rest_framework.exceptions import ValidationError


def object_data(request):
    if not isinstance(request.data, dict):
        raise ValidationError('请求参数必须为对象')
    return request.data


def query_id(params, name):
    value = params.get(name)
    if value in (None, ''):
        return None
    return serializers.IntegerField(min_value=1).run_validation(value)
