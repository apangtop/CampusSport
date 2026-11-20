from CampusSport.input_validation import object_data, query_id
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from django.db import transaction
from django.shortcuts import get_object_or_404
from .models import User
from .serializers import (
    UserSerializer, UserCreateSerializer, UserUpdateSerializer,
    ChangePasswordSerializer, LoginResponseSerializer
)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        data['user'] = {
            'id': user.id,
            'username': user.username,
            'real_name': user.real_name,
            'role': user.role,
            'class_name': user.class_name,
        }
        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class CheckedTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        from rest_framework_simplejwt.settings import api_settings
        from rest_framework_simplejwt.utils import get_md5_hash_password
        from rest_framework.exceptions import AuthenticationFailed
        token = self.token_class(attrs['refresh'])
        user = User.objects.filter(pk=token.get(api_settings.USER_ID_CLAIM), is_active=True).first()
        if not user or token.get(api_settings.REVOKE_TOKEN_CLAIM) != get_md5_hash_password(user.password):
            raise AuthenticationFailed('登录已失效，请重新登录')
        return super().validate(attrs)


class CheckedTokenRefreshView(TokenRefreshView):
    serializer_class = CheckedTokenRefreshSerializer


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'


class UserViewSet(viewsets.ModelViewSet):
    def _lock_admins(self, target):
        from rest_framework.exceptions import ValidationError
        admins = list(User.objects.select_for_update().filter(role='admin').order_by('pk'))
        current = next((user for user in admins if user.pk == target.pk), None)
        if current and current.is_active and not any(user.is_active and user.pk != current.pk for user in admins):
            raise ValidationError('不能停用或删除最后一个启用的管理员账号')

    def perform_update(self, serializer):
        from django.db import transaction
        with transaction.atomic():
            if serializer.validated_data.get('is_active') is False:
                self._lock_admins(serializer.instance)
            serializer.instance = get_object_or_404(User.objects.select_for_update(),pk=serializer.instance.pk)
            serializer.save()

    def perform_destroy(self, instance):
        from django.db import transaction
        with transaction.atomic():
            self._lock_admins(instance)
            instance = get_object_or_404(User.objects.select_for_update(),pk=instance.pk)
            instance.delete()

    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        if self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ['create', 'destroy', 'update', 'partial_update']:
            return [IsAdmin()]
        if self.action == 'list':
            return [IsAdmin()]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            qs = User.objects.all()
            role = self.request.query_params.get('role')
            if role:
                qs = qs.filter(role=role)
            return qs
        return User.objects.filter(id=user.id)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    @transaction.atomic
    def change_password(self, request, pk=None):
        user = get_object_or_404(User.objects.select_for_update(),pk=self.get_object().pk)
        if request.user != user and request.user.role != 'admin':
            return Response({'detail': '无权限'}, status=status.HTTP_403_FORBIDDEN)
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            if not user.check_password(serializer.validated_data['old_password']):
                return Response({'old_password': ['原密码错误']}, status=status.HTTP_400_BAD_REQUEST)
            user.set_password(serializer.validated_data['new_password'])
            user.save(update_fields=['password'])
            return Response({'detail': '密码修改成功'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    @transaction.atomic
    def reset_password(self, request, pk=None):
        user = get_object_or_404(User.objects.select_for_update(),pk=self.get_object().pk)
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError as DjangoValidationError
        from rest_framework.exceptions import ValidationError
        new_password = object_data(request).get('new_password')
        if not isinstance(new_password, str) or not new_password:
            raise ValidationError({'new_password': ['请输入新密码']})
        try:
            validate_password(new_password, user)
        except DjangoValidationError as exc:
            raise ValidationError({'new_password': exc.messages})
        user.set_password(new_password)
        user.save(update_fields=['password'])
        return Response({'detail': '密码已重置'})
