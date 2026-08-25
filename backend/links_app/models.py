from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import URLValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class PublishableModel(models.Model):
    """Shared visibility/scheduling behaviour for public content items
    (songs, albums, media, concerts): a record can be hidden entirely, be
    published normally, be scheduled to appear at a future date/time, or
    show up right away as a "coming soon" teaser that fully opens at
    publish_at.
    """

    class Visibility(models.TextChoices):
        DRAFT = 'DRAFT', _('Hidden (draft)')
        SCHEDULED = 'SCHEDULED', _('Scheduled')
        COMING_SOON = 'COMING_SOON', _('Coming Soon')
        PUBLISHED = 'PUBLISHED', _('Published')

    visibility = models.CharField(
        max_length=15, choices=Visibility.choices, default=Visibility.PUBLISHED, db_index=True,
    )
    publish_at = models.DateTimeField(
        null=True, blank=True,
        help_text=_('When this becomes fully visible/open (used by Scheduled and Coming Soon).'),
    )

    class Meta:
        abstract = True

    @property
    def is_live(self):
        """Whether the full content should be considered open/available now."""
        if self.visibility == self.Visibility.PUBLISHED:
            return True
        if self.visibility in (self.Visibility.SCHEDULED, self.Visibility.COMING_SOON):
            return bool(self.publish_at) and timezone.now() >= self.publish_at
        return False

    @property
    def is_visible_in_listing(self):
        """Whether it should appear publicly at all (as a teaser or in full)."""
        if self.visibility == self.Visibility.DRAFT:
            return False
        if self.visibility == self.Visibility.SCHEDULED:
            return self.is_live
        return True

    @classmethod
    def visible_queryset(cls, queryset):
        """Rows a public (unauthenticated) caller should see: excludes
        drafts, and excludes scheduled rows whose publish_at hasn't hit yet.
        """
        now = timezone.now()
        return queryset.exclude(
            Q(visibility=cls.Visibility.DRAFT)
            | Q(visibility=cls.Visibility.SCHEDULED, publish_at__isnull=True)
            | Q(visibility=cls.Visibility.SCHEDULED, publish_at__gt=now)
        )


class Platform(models.Model):
    class Name(models.TextChoices):
        YOUTUBE = 'YOUTUBE', _('YouTube')
        SPOTIFY = 'SPOTIFY', _('Spotify')
        ANGHAMI = 'ANGHAMI', _('Anghami')
        APPLE_MUSIC = 'APPLE_MUSIC', _('Apple Music')
        NETFLIX = 'NETFLIX', _('Netflix')
        SHAHID = 'SHAHID', _('Shahid')
        WATCH_IT = 'WATCH_IT', _('WATCH IT')
        OTHER = 'OTHER', _('Other')

    platform_name = models.CharField(max_length=20, choices=Name.choices, default=Name.OTHER, unique=True)
    logo_icon_url = models.URLField(blank=True, validators=[URLValidator(schemes=['http', 'https'])])

    class Meta:
        ordering = ('platform_name',)

    def __str__(self):
        return self.get_platform_name_display()


class ExternalLink(models.Model):
    """Links a Person, Album, Song, or Media item (movie/series/commercial/
    program), or Concert to where it can be found externally (a YouTube
    channel, a song's Spotify page, ...). Generic so every domain shares
    one mapper table instead of duplicating link models.
    """

    class AccessType(models.TextChoices):
        FREE = 'FREE', _('Free')
        SUBSCRIPTION = 'SUBSCRIPTION', _('Subscription')
        RENTAL = 'RENTAL', _('Rental')
        PURCHASE = 'PURCHASE', _('Purchase')

    platform = models.ForeignKey(Platform, on_delete=models.PROTECT, related_name='links')

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to=(
            Q(app_label='people_app', model='person')
            | Q(app_label='music_app', model='album')
            | Q(app_label='music_app', model='song')
            | Q(app_label='media_app', model='media')
            | Q(app_label='concerts_app', model='concert')
        ),
    )
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    direct_url = models.URLField(validators=[URLValidator(schemes=['http', 'https'])])
    embed_code = models.TextField(blank=True)
    access_type = models.CharField(max_length=15, choices=AccessType.choices, default=AccessType.FREE)

    class Meta:
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['platform']),
        ]

    def __str__(self):
        return f'{self.platform} -> {self.direct_url}'
