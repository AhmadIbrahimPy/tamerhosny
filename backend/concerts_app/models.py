from django.contrib.contenttypes.fields import GenericRelation
from django.core.validators import URLValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from backend.links_app.models import ExternalLink, HeroMediaMixin, PublishableModel
from backend.main_app.shared_utils.slugs import generate_ascii_slug
from backend.studios_app.models import Studio


class Concert(PublishableModel, HeroMediaMixin):
    class Status(models.TextChoices):
        UPCOMING = 'UPCOMING', _('Upcoming')
        COMPLETED = 'COMPLETED', _('Completed')
        CANCELLED = 'CANCELLED', _('Cancelled')
        POSTPONED = 'POSTPONED', _('Postponed')

    title_ar = models.CharField(max_length=200)
    title_en = models.CharField(max_length=200, blank=True)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.UPCOMING, db_index=True)

    date = models.DateTimeField(null=True, blank=True, help_text='Leave blank for "date TBA" upcoming concerts.')
    venue_name = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=120, blank=True)
    country = models.CharField(max_length=120, blank=True)

    description = models.TextField(blank=True)
    poster_image = models.ImageField(upload_to='concerts/posters/', blank=True, null=True)
    poster_url = models.URLField(blank=True, validators=[URLValidator(schemes=['http', 'https'])])
    organizer = models.ForeignKey(
        Studio, on_delete=models.SET_NULL, null=True, blank=True, related_name='organized_concerts',
    )

    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    links = GenericRelation(ExternalLink)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-date',)
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['date']),
            models.Index(fields=['slug']),
            models.Index(fields=['visibility']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_ascii_slug(Concert, self.title_en, 'concert')
        super().save(*args, **kwargs)

    @property
    def is_upcoming(self):
        return self.status == self.Status.UPCOMING or (self.date and self.date >= timezone.now())

    @property
    def display_poster_url(self):
        if self.poster_image:
            return self.poster_image.url
        return self.poster_url

    @property
    def has_location(self):
        return self.latitude is not None and self.longitude is not None

    def __str__(self):
        return f'{self.title_ar} - {self.city or "TBA"}'
