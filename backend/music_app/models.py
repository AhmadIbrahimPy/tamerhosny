from datetime import date

from django.contrib.contenttypes.fields import GenericRelation
from django.core.validators import MaxValueValidator, MinValueValidator, URLValidator
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from backend.links_app.models import ExternalLink, PublishableModel
from backend.media_app.models import Media
from backend.people_app.models import Person
from backend.studios_app.models import Studio


class Album(PublishableModel):
    title_ar = models.CharField(max_length=200)
    title_en = models.CharField(max_length=200, blank=True)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    release_date = models.DateField(null=True, blank=True)
    cover_image = models.ImageField(upload_to='albums/covers/', blank=True, null=True)
    cover_art_url = models.URLField(blank=True, validators=[URLValidator(schemes=['http', 'https'])])
    record_label = models.ForeignKey(
        Studio, on_delete=models.SET_NULL, null=True, blank=True, related_name='albums',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-release_date', 'title_ar')
        indexes = [
            models.Index(fields=['release_date']),
            models.Index(fields=['visibility']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title_en or self.title_ar, allow_unicode=True)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title_ar


class Song(PublishableModel):
    class SongType(models.TextChoices):
        SINGLE = 'SINGLE', _('Single')
        ALBUM_TRACK = 'ALBUM_TRACK', _('Album Track')
        MOVIE_THEME = 'MOVIE_THEME', _('Movie Theme')
        SERIES_THEME = 'SERIES_THEME', _('Series Theme')
        COMMERCIAL_JINGLE = 'COMMERCIAL_JINGLE', _('Commercial Jingle')
        RELIGIOUS = 'RELIGIOUS', _('Religious / Duaa')

    title_ar = models.CharField(max_length=200)
    title_en = models.CharField(max_length=200, blank=True)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    cover_image = models.ImageField(upload_to='songs/covers/', blank=True, null=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(1)])
    lyrics = models.TextField(blank=True)
    release_year = models.PositiveSmallIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1900), MaxValueValidator(date.today().year + 1)],
    )
    song_type = models.CharField(max_length=20, choices=SongType.choices, default=SongType.SINGLE, db_index=True)
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
            models.Index(fields=['visibility']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title_en or self.title_ar, allow_unicode=True)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title_ar


class SongCredit(models.Model):
    class Role(models.TextChoices):
        SINGER = 'SINGER', _('Singer')
        LYRICIST = 'LYRICIST', _('Lyricist / Poet')
        COMPOSER = 'COMPOSER', _('Composer')
        ARRANGER = 'ARRANGER', _('Arranger')
        MUSIC_PRODUCER = 'MUSIC_PRODUCER', _('Music Producer')
        RECORDING_ENGINEER = 'RECORDING_ENGINEER', _('Recording Engineer')
        MIX_MASTER_ENGINEER = 'MIX_MASTER_ENGINEER', _('Mix & Master Engineer')
        FEATURED_ARTIST = 'FEATURED_ARTIST', _('Featured Artist')

    song = models.ForeignKey(Song, on_delete=models.CASCADE, related_name='credits')
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='song_credits')
    role = models.CharField(max_length=25, choices=Role.choices, db_index=True)

    class Meta:
        unique_together = ('song', 'person', 'role')

    def __str__(self):
        return f'{self.person} - {self.role} - {self.song}'


class SongLyricSegment(models.Model):
    """One timed segment of a song's timeline: a stretch of lyrics, an
    instrumental passage, or silence, each spanning [start_seconds,
    end_seconds). Segments are meant to be added back-to-back — a new one
    normally starts exactly where the previous one ended.
    """

    class SegmentType(models.TextChoices):
        LYRICS = 'LYRICS', _('Lyrics')
        MUSIC = 'MUSIC', _('Music (instrumental)')
        SILENCE = 'SILENCE', _('Silence')

    song = models.ForeignKey(Song, on_delete=models.CASCADE, related_name='lyric_segments')
    start_seconds = models.DecimalField(max_digits=7, decimal_places=2, validators=[MinValueValidator(0)])
    end_seconds = models.DecimalField(max_digits=7, decimal_places=2, validators=[MinValueValidator(0)])
    segment_type = models.CharField(max_length=10, choices=SegmentType.choices, default=SegmentType.LYRICS)
    text = models.TextField(blank=True, help_text=_('Required only when the segment type is Lyrics.'))

    class Meta:
        ordering = ('start_seconds',)
        indexes = [models.Index(fields=['song', 'start_seconds'])]

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.end_seconds is not None and self.start_seconds is not None and self.end_seconds <= self.start_seconds:
            raise ValidationError(_('End time must be after start time.'))
        if self.segment_type == self.SegmentType.LYRICS and not self.text.strip():
            raise ValidationError(_('Text is required for a lyrics segment.'))

    def __str__(self):
        return f'{self.song} [{self.start_seconds}s–{self.end_seconds}s] {self.get_segment_type_display()}'
