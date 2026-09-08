from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from backend.main_app.models import UserAccount, VoiceAssistantLog


@admin.register(UserAccount)
class UserAccountAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + ((None, {'fields': ('role',)}),)
    list_display = ('username', 'email', 'role', 'is_active', 'is_staff')


@admin.register(VoiceAssistantLog)
class VoiceAssistantLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'event_type', 'user', 'client_session_id', 'ms_value', 'detail', 'transcript')
    list_filter = ('event_type',)
    search_fields = ('client_session_id', 'transcript', 'detail', 'user_agent', 'user__username')
    readonly_fields = [f.name for f in VoiceAssistantLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
