from django.contrib import admin

from backend.analytics_app.models import AnalyticsEvent


@admin.register(AnalyticsEvent)
class AnalyticsEventAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'content_type', 'object_id', 'platform', 'share_channel', 'created_at')
    list_filter = ('event_type', 'content_type', 'platform', 'share_channel')
    date_hierarchy = 'created_at'
