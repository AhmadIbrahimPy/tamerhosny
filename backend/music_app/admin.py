from django.contrib import admin

from backend.music_app.models import Album, Song, SongCredit, SongLyricSegment


class SongCreditInline(admin.TabularInline):
    model = SongCredit
    extra = 1


class SongLyricSegmentInline(admin.TabularInline):
    model = SongLyricSegment
    extra = 1


@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ('title_ar', 'release_date', 'record_label', 'visibility')
    list_filter = ('record_label',)
    search_fields = ('title_ar', 'title_en')
    prepopulated_fields = {'slug': ('title_ar',)}


@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ('title_ar', 'song_type', 'album', 'release_year', 'is_duet', 'visibility')
    search_fields = ('title_ar', 'title_en')
    list_filter = ('song_type', 'album', 'is_duet')
    prepopulated_fields = {'slug': ('title_ar',)}
    inlines = [SongCreditInline, SongLyricSegmentInline]
