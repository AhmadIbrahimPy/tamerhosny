from datetime import date

from django.contrib.contenttypes.fields import GenericRelation
from django.core.validators import MaxValueValidator, MinValueValidator, URLValidator
from django.db import models
from django.utils.text import slugify

from backend.links_app.models import ExternalLink
from backend.media_app.models import Media
from backend.people_app.models import Person
from backend.studios_app.models import Studio


class Album(models.Model):
    title_ar = models.CharField(max_length=200)
    title_en = models.CharField(max_length=200, blank=True)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    release_date = models.DateField(null=True, blank=True)
    cover_art_url = models.URLField(blank=True, validators=[URLValidator(schemes=['http', 'https'])])
    record_label = models.ForeignKey(
        Studio, on_delete=models.SET_NULL, null=True, blank=True, related_name='albums',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-release_date', 'title_ar')
        indexes = [models.Index(fields=['release_date'])]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title_en or self.title_ar, allow_unicode=True)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title_ar


class Song(models.Model):
    class SongType(models.TextChoices):
        SINGLE = 'SINGLE', 'Single'
        ALBUM_TRACK = 'ALBUM_TRACK', 'Album Track'
        MOVIE_THEME = 'MOVIE_THEME', 'Movie Theme'
        SERIES_THEME = 'SERIES_THEME', 'Series Theme'
        COMMERCIAL_JINGLE = 'COMMERCIAL_JINGLE', 'Commercial Jingle'
        RELIGIOUS = 'RELIGIOUS', 'Religious / Duaa'

    title_ar = models.CharField(max_length=200)
    title_en = models.CharField(max_length=200, blank=True)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(1)])
    lyrics = models.TextField(blank=True)
    release_year = models.PositiveSmallIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1900), MaxValueValidator(date.today().year + 1)],
    )
    song_type = models.CharField(max_length=20, choices=SongType.choices, db_index=True)
    is_duet = models.BooleanField(default=False)

    recording_studio = models.ForeignKey(
        Studio, on_delete=models.SET_NULL, null=True, blank=True, related_name='recorded_songs',
    )
    album = models.ForeignKey(Album, on_delete=models.SET_NULL, null=True, blank=True, related_name='songs')
    related_media = models.ForeignKey(
        Media, on_delete=models.SET_NULL, null=True, blank=True, related_name='theme_songs',
        help_text='Set when the song was created specifically for a movie/series/commercial.',
    )

    links = GenericRelation(ExternalLink)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-release_year', 'title_ar')
        indexes = [
            models.Index(fields=['release_year']),
            models.Index(fields=['song_type']),
            models.Index(fields=['slug']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title_en or self.title_ar, allow_unicode=True)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title_ar


class SongCredit(models.Model):
    class Role(models.TextChoices):
        SINGER = 'SINGER', 'Singer'
        LYRICIST = 'LYRICIST', 'Lyricist / Poet'
        COMPOSER = 'COMPOSER', 'Composer'
        ARRANGER = 'ARRANGER', 'Arranger'
        MUSIC_PRODUCER = 'MUSIC_PRODUCER', 'Music Producer'
        RECORDING_ENGINEER = 'RECORDING_ENGINEER', 'Recording Engineer'
        MIX_MASTER_ENGINEER = 'MIX_MASTER_ENGINEER', 'Mix & Master Engineer'
        FEATURED_ARTIST = 'FEATURED_ARTIST', 'Featured Artist'

    song = models.ForeignKey(Song, on_delete=models.CASCADE, related_name='credits')
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='song_credits')
    role = models.CharField(max_length=25, choices=Role.choices, db_index=True)

    class Meta:
        unique_together = ('song', 'person', 'role')

    def __str__(self):
        return f'{self.person} - {self.role} - {self.song}'
