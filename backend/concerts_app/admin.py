from django.contrib import admin

from backend.concerts_app.models import Concert


@admin.register(Concert)
class ConcertAdmin(admin.ModelAdmin):
    list_display = ('title_ar', 'status', 'date', 'city', 'country', 'visibility')
    list_filter = ('status', 'country')
    search_fields = ('title_ar', 'title_en', 'city', 'venue_name')
    prepopulated_fields = {'slug': ('title_ar',)}
