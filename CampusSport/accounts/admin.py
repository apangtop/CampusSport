from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'real_name', 'role', 'class_name', 'is_active']
    list_filter = ['role', 'is_active']
    search_fields = ['username', 'real_name']
    fieldsets = UserAdmin.fieldsets + (
        ('角色信息', {'fields': ('role', 'real_name', 'phone', 'class_name')}),
    )
