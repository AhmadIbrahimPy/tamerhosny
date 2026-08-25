from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import URLValidator
from django.db import models
from django.db.models import Q


class Platform(models.Model):
    class Name(models.TextChoices):
        YOUTUBE = 'YOUTUBE', 'YouTube'
        SPOTIFY = 'SPOTIFY', 'Spotify'
        ANGHAMI = 'ANGHAMI', 'Anghami'
        APPLE_MUSIC = 'APPLE_MUSIC', 'Apple Music'
        NETFLIX = 'NETFLIX', 'Netflix'
        SHAHID = 'SHAHID', 'Shahid'
        WATCH_IT = 'WATCH_IT', 'WATCH IT'
        OTHER = 'OTHER', 'Other'

    platform_name = models.CharField(max_length=20, choices=Name.choices, unique=True)
    logo_icon_url = models.URLField(blank=True, validators=[URLValidator(schemes=['http', 'https'])])

    class Meta:
        ordering = ('platform_name',)

    def __str__(self):
        return self.get_platform_name_display()


class ExternalLink(models.Model):
    """Links a Song or a Media item (movie/series/commercial/program) to
    where it can be streamed/watched externally. Generic so both domains
    share one mapper table instead of duplicating link models.
    """

    class AccessType(models.TextChoices):
        FREE = 'FREE', 'Free'
        SUBSCRIPTION = 'SUBSCRIPTION', 'Subscription'
        RENTAL = 'RENTAL', 'Rental'
        PURCHASE = 'PURCHASE', 'Purchase'

    platform = models.ForeignKey(Platform, on_delete=models.PROTECT, related_name='links')

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to=(
            Q(app_label='music_app', model='song')
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
