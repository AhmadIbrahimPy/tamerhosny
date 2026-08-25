from django.contrib import admin

from backend.ads_app.models import Advertisement


@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'show_on_all_pages', 'content_type', 'object_id', 'created_at')
    list_filter = ('is_active', 'show_on_all_pages')
    search_fields = ('title', 'external_url')
