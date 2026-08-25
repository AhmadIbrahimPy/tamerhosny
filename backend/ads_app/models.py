from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import URLValidator
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

# kind (content_type.model) -> website_app detail url name, used to build
# the click-through link when an ad is attached to an existing content item.
_DETAIL_URL_NAMES = {
    'person': 'website_app:person-detail',
    'album': 'website_app:album-detail',
    'song': 'website_app:song-detail',
    'media': 'website_app:media-detail',
    'concert': 'website_app:concert-detail',
}


class Advertisement(models.Model):
    """A promotional banner shown on the public website: it can point at
    an existing content item (song/album/media/concert/person), at an
    outside website, or at nothing at all (a purely informational
    banner). Placement controls which public pages it can appear on.
    """

    class Placement(models.TextChoices):
        HOME = 'HOME', _('Home Page')
        PEOPLE = 'PEOPLE', _('Artists & Crew Pages')
        SONGS = 'SONGS', _('Songs Pages')
        ALBUMS = 'ALBUMS', _('Albums Pages')
        MEDIA = 'MEDIA', _('Movies & Series Pages')
        CONCERTS = 'CONCERTS', _('Concerts Pages')

    title = models.CharField(max_length=200)
    image = models.ImageField(upload_to='ads/')
    is_active = models.BooleanField(default=True)

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        limit_choices_to=(
            Q(app_label='people_app', model='person')
            | Q(app_label='music_app', model='album')
            | Q(app_label='music_app', model='song')
            | Q(app_label='media_app', model='media')
            | Q(app_label='concerts_app', model='concert')
        ),
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    external_url = models.URLField(blank=True, validators=[URLValidator(schemes=['http', 'https'])])

    show_on_all_pages = models.BooleanField(default=True)
    placements = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self):
        return self.title

    @property
    def is_linked_internally(self):
        return self.content_object is not None

    @property
    def is_linked_externally(self):
        return bool(self.external_url) and not self.is_linked_internally

    def shows_on(self, placement):
        return self.show_on_all_pages or placement in (self.placements or [])

    def get_target_url(self):
        if self.content_object is not None:
            url_name = _DETAIL_URL_NAMES.get(self.content_type.model)
            if url_name and getattr(self.content_object, 'slug', None):
                return reverse(url_name, args=[self.content_object.slug])
        return self.external_url
