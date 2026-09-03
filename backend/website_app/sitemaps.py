from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from backend.concerts_app.models import Concert
from backend.media_app.models import Media
from backend.music_app.models import Album, Song
from backend.people_app.models import Person


class StaticViewSitemap(Sitemap):
    changefreq = 'daily'
    priority = 0.8

    def items(self):
        return ['home', 'songs', 'albums', 'movies', 'series', 'commercials', 'concerts', 'people']

    def location(self, item):
        return reverse(f'website_app:{item}')


class SongSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.7

    def items(self):
        return Song.visible_queryset(Song.objects.all())

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('website_app:song-detail', args=[obj.slug])


class AlbumSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.6

    def items(self):
        return Album.visible_queryset(Album.objects.all())

    def location(self, obj):
        return reverse('website_app:album-detail', args=[obj.slug])


class MovieSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.6

    def items(self):
        return Media.visible_queryset(Media.objects.filter(media_type=Media.MediaType.MOVIE))

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('website_app:media-detail', args=[obj.slug])


class SeriesSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.6

    def items(self):
        return Media.visible_queryset(Media.objects.filter(media_type=Media.MediaType.TV_SERIES))

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('website_app:media-detail', args=[obj.slug])


class CommercialSitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.5

    def items(self):
        return Media.visible_queryset(Media.objects.filter(media_type=Media.MediaType.COMMERCIAL))

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('website_app:media-detail', args=[obj.slug])


class ConcertSitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.5

    def items(self):
        return Concert.visible_queryset(Concert.objects.all())

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('website_app:concert-detail', args=[obj.slug])


class PersonSitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.5

    def items(self):
        return Person.objects.all()

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('website_app:person-detail', args=[obj.slug])


sitemaps = {
    'static': StaticViewSitemap,
    'songs': SongSitemap,
    'albums': AlbumSitemap,
    'movies': MovieSitemap,
    'series': SeriesSitemap,
    'commercials': CommercialSitemap,
    'concerts': ConcertSitemap,
    'people': PersonSitemap,
}
