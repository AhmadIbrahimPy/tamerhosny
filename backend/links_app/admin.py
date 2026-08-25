from django.contrib import admin

from backend.links_app.models import ExternalLink, Platform


@admin.register(Platform)
class PlatformAdmin(admin.ModelAdmin):
    list_display = ('platform_name',)


@admin.register(ExternalLink)
class ExternalLinkAdmin(admin.ModelAdmin):
    list_display = ('platform', 'direct_url', 'access_type', 'content_type', 'object_id')
    list_filter = ('platform', 'access_type')
