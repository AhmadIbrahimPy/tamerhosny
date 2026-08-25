from django.contrib import admin

from backend.media_app.models import Media, MediaCredit


class MediaCreditInline(admin.TabularInline):
    model = MediaCredit
    extra = 1


@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = ('title_ar', 'media_type', 'release_date', 'rating', 'visibility')
    list_filter = ('media_type',)
    search_fields = ('title_ar', 'title_en')
    prepopulated_fields = {'slug': ('title_ar',)}
    inlines = [MediaCreditInline]
