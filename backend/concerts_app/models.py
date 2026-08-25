from django.contrib.contenttypes.fields import GenericRelation
from django.core.validators import URLValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from backend.links_app.models import ExternalLink
from backend.studios_app.models import Studio


class Concert(models.Model):
    class Status(models.TextChoices):
        UPCOMING = 'UPCOMING', 'Upcoming'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'
        POSTPONED = 'POSTPONED', 'Postponed'

    title_ar = models.CharField(max_length=200)
    title_en = models.CharField(max_length=200, blank=True)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.UPCOMING, db_index=True)

    date = models.DateTimeField(null=True, blank=True, help_text='Leave blank for "date TBA" upcoming concerts.')
    venue_name = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=120, blank=True)
    country = models.CharField(max_length=120, blank=True)

    description = models.TextField(blank=True)
    poster_url = models.URLField(blank=True, validators=[URLValidator(schemes=['http', 'https'])])
    organizer = models.ForeignKey(
        Studio, on_delete=models.SET_NULL, null=True, blank=True, related_name='organized_concerts',
    )

    links = GenericRelation(ExternalLink)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-date',)
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['date']),
            models.Index(fields=['slug']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title_en or self.title_ar, allow_unicode=True)
        super().save(*args, **kwargs)

    @property
    def is_upcoming(self):
        return self.status == self.Status.UPCOMING or (self.date and self.date >= timezone.now())

    def __str__(self):
        return f'{self.title_ar} - {self.city or "TBA"}'
