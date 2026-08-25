from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext_lazy as _

from backend.ads_app.models import Advertisement
from backend.concerts_app.models import Concert
from backend.media_app.models import Media
from backend.music_app.models import Album, Song
from backend.people_app.models import Person

PAGE_SIZE = 12


def _paginate(request, queryset):
    return Paginator(queryset, PAGE_SIZE).get_page(request.GET.get('page'))


def _ad_for(placement):
    """The banner ad to show on a given public page, if any (either
    targeted at this placement specifically, or set to show everywhere).
    """
    return (
        Advertisement.objects.filter(is_active=True)
        .filter(Q(show_on_all_pages=True) | Q(placements__contains=[placement]))
        .order_by('?')
        .first()
    )


def home(request):
    songs = Song.visible_queryset(Song.objects.select_related('album'))[:8]
    movies = Media.visible_queryset(Media.objects.filter(media_type=Media.MediaType.MOVIE))[:6]
    series = Media.visible_queryset(Media.objects.filter(media_type=Media.MediaType.TV_SERIES))[:6]
    albums = Album.visible_queryset(Album.objects.all())[:6]
    concerts = Concert.visible_queryset(Concert.objects.all())[:4]
    people = Person.objects.all()[:8]
    return render(request, 'website/pages/home.html', {
        'songs': songs,
        'movies': movies,
        'series': series,
        'albums': albums,
        'concerts': concerts,
        'people': people,
        'page_ad': _ad_for(Advertisement.Placement.HOME),
    })


# ---------------------------------------------------------------------------
# People
# ---------------------------------------------------------------------------

def people_list(request):
    people = _paginate(request, Person.objects.all())
    return render(request, 'website/pages/people/list.html', {
        'people': people,
        'page_ad': _ad_for(Advertisement.Placement.PEOPLE),
    })


def person_detail(request, slug):
    person = get_object_or_404(Person, slug=slug)
    song_credits = person.song_credits.select_related('song', 'song__album').order_by('-song__release_year')
    media_credits = person.media_credits.select_related('media').order_by('-media__release_date')
    related_people = Person.objects.exclude(pk=person.pk).order_by('?')[:6]
    return render(request, 'website/pages/people/detail.html', {
        'person': person,
        'song_credits': song_credits,
        'media_credits': media_credits,
        'links': person.links.select_related('platform').all(),
        'related_people': related_people,
        'page_ad': _ad_for(Advertisement.Placement.PEOPLE),
    })


# ---------------------------------------------------------------------------
# Songs
# ---------------------------------------------------------------------------

def songs_list(request):
    queryset = Song.visible_queryset(Song.objects.select_related('album')).order_by('-release_year')
    songs = _paginate(request, queryset)
    return render(request, 'website/pages/songs/list.html', {
        'songs': songs,
        'page_ad': _ad_for(Advertisement.Placement.SONGS),
    })


def song_detail(request, slug):
    song = get_object_or_404(
        Song.objects.select_related('album', 'related_media', 'recording_studio'), slug=slug,
    )
    related_qs = Song.objects.select_related('album')
    if song.album_id:
        related_qs = related_qs.filter(album_id=song.album_id)
    else:
        related_qs = related_qs.filter(song_type=song.song_type)
    related_songs = Song.visible_queryset(related_qs).exclude(pk=song.pk)[:6]
    return render(request, 'website/pages/songs/detail.html', {
        'song': song,
        'credits': song.credits.select_related('person').all(),
        'links': song.links.select_related('platform').all(),
        'related_songs': related_songs,
        'page_ad': _ad_for(Advertisement.Placement.SONGS),
    })


# ---------------------------------------------------------------------------
# Albums
# ---------------------------------------------------------------------------

def albums_list(request):
    queryset = Album.visible_queryset(Album.objects.all()).order_by('-release_date')
    albums = _paginate(request, queryset)
    return render(request, 'website/pages/albums/list.html', {
        'albums': albums,
        'page_ad': _ad_for(Advertisement.Placement.ALBUMS),
    })


def album_detail(request, slug):
    album = get_object_or_404(Album, slug=slug)
    songs = Song.visible_queryset(album.songs.all())
    related_albums = Album.visible_queryset(Album.objects.exclude(pk=album.pk)).order_by('-release_date')[:6]
    return render(request, 'website/pages/albums/detail.html', {
        'album': album,
        'songs': songs,
        'links': album.links.select_related('platform').all(),
        'related_albums': related_albums,
        'page_ad': _ad_for(Advertisement.Placement.ALBUMS),
    })


# ---------------------------------------------------------------------------
# Media — movies, series and commercials are fully separate browse pages
# (though they share one Media model/detail template).
# ---------------------------------------------------------------------------

def _media_section_list(request, media_type, template_title):
    queryset = Media.visible_queryset(Media.objects.filter(media_type=media_type)).order_by('-release_date')
    media_items = _paginate(request, queryset)
    return render(request, 'website/pages/media/list.html', {
        'media_items': media_items,
        'list_title': template_title,
        'page_ad': _ad_for(Advertisement.Placement.MEDIA),
    })


def movies_list(request):
    return _media_section_list(request, Media.MediaType.MOVIE, _('الأفلام'))


def series_list(request):
    return _media_section_list(request, Media.MediaType.TV_SERIES, _('المسلسلات'))


def commercials_list(request):
    return _media_section_list(request, Media.MediaType.COMMERCIAL, _('الإعلانات والحملات الترويجية'))


def media_detail(request, slug):
    media = get_object_or_404(Media, slug=slug)
    related_media = Media.visible_queryset(
        Media.objects.filter(media_type=media.media_type).exclude(pk=media.pk)
    ).order_by('-release_date')[:6]
    return render(request, 'website/pages/media/detail.html', {
        'media': media,
        'credits': media.credits.select_related('person').all(),
        'links': media.links.select_related('platform').all(),
        'theme_songs': Song.visible_queryset(media.theme_songs.all()),
        'related_media': related_media,
        'page_ad': _ad_for(Advertisement.Placement.MEDIA),
    })


# ---------------------------------------------------------------------------
# Concerts
# ---------------------------------------------------------------------------

def concerts_list(request):
    queryset = Concert.visible_queryset(Concert.objects.select_related('organizer')).order_by('-date')
    concerts = _paginate(request, queryset)
    return render(request, 'website/pages/concerts/list.html', {
        'concerts': concerts,
        'page_ad': _ad_for(Advertisement.Placement.CONCERTS),
    })


def concert_detail(request, slug):
    concert = get_object_or_404(Concert, slug=slug)
    related_concerts = Concert.visible_queryset(
        Concert.objects.exclude(pk=concert.pk)
    ).order_by('-date')[:6]
    return render(request, 'website/pages/concerts/detail.html', {
        'concert': concert,
        'links': concert.links.select_related('platform').all(),
        'related_concerts': related_concerts,
        'page_ad': _ad_for(Advertisement.Placement.CONCERTS),
    })
