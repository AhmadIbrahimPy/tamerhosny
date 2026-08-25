from django.contrib import admin

from backend.music_app.models import Album, Song, SongCredit


class SongCreditInline(admin.TabularInline):
    model = SongCredit
    extra = 1


@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ('title', 'release_date')
    search_fields = ('title',)
    prepopulated_fields = {'slug': ('title',)}


@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ('title', 'album', 'release_date')
    search_fields = ('title',)
    list_filter = ('album',)
    prepopulated_fields = {'slug': ('title',)}
    inlines = [SongCreditInline]
