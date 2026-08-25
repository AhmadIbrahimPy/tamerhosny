from django.contrib import admin

from backend.studios_app.models import Studio


@admin.register(Studio)
class StudioAdmin(admin.ModelAdmin):
    list_display = ('name', 'entity_type')
    list_filter = ('entity_type',)
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
