from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from backend.main_app.models import UserAccount


@admin.register(UserAccount)
class UserAccountAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + ((None, {'fields': ('role',)}),)
    list_display = ('username', 'email', 'role', 'is_active', 'is_staff')
