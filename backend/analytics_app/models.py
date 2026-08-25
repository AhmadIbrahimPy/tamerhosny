from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _


class AnalyticsEvent(models.Model):
    """One tracked interaction from the public website: a page open, a
    play, a share, or a click-through to an external platform. Generic so
    every content type (person/song/album/media/concert) shares one table.
    """

    class EventType(models.TextChoices):
        VIEW = 'VIEW', _('Page View')
        PLAY = 'PLAY', _('Play')
        SHARE = 'SHARE', _('Share')
        EXTERNAL_CLICK = 'EXTERNAL_CLICK', _('External Platform Click')

    class ShareChannel(models.TextChoices):
        WHATSAPP = 'WHATSAPP', _('WhatsApp')
        FACEBOOK = 'FACEBOOK', _('Facebook')
        TWITTER = 'TWITTER', _('X / Twitter')
        TELEGRAM = 'TELEGRAM', _('Telegram')
        COPY_LINK = 'COPY_LINK', _('Copy Link')
        OTHER = 'OTHER', _('Other')

    event_type = models.CharField(max_length=20, choices=EventType.choices, db_index=True)

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to=(
            Q(app_label='people_app', model='person')
            | Q(app_label='studios_app', model='studio')
            | Q(app_label='music_app', model='album')
            | Q(app_label='music_app', model='song')
            | Q(app_label='media_app', model='media')
            | Q(app_label='concerts_app', model='concert')
            | Q(app_label='ads_app', model='advertisement')
        ),
    )
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    # Only set when event_type == EXTERNAL_CLICK.
    platform = models.ForeignKey(
        'links_app.Platform', on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
    )
    external_link = models.ForeignKey(
        'links_app.ExternalLink', on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
    )

    # Only set when event_type == SHARE.
    share_channel = models.CharField(max_length=15, choices=ShareChannel.choices, blank=True)

    session_key = models.CharField(max_length=64, blank=True, db_index=True)
    referrer = models.URLField(blank=True, max_length=500)
    user_agent = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=['event_type', 'content_type', 'object_id']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f'{self.get_event_type_display()} - {self.content_object} - {self.created_at:%Y-%m-%d %H:%M}'
