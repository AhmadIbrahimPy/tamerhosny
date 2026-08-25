from django.contrib.contenttypes.fields import GenericRelation
from django.core.validators import MaxValueValidator, MinValueValidator, URLValidator
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from backend.links_app.models import ExternalLink, PublishableModel
from backend.people_app.models import Person


class Media(PublishableModel):
    """Base model for every non-song production: movies, TV series,
    commercials and TV programs/shows. One table with a discriminator
    (media_type) rather than per-type tables, since the shared fields
    (title, release_date, poster, cast & crew, links) dominate.
    """

    class MediaType(models.TextChoices):
        MOVIE = 'MOVIE', _('Movie')
        TV_SERIES = 'TV_SERIES', _('TV Series')
        COMMERCIAL = 'COMMERCIAL', _('Commercial')
        PROGRAM = 'PROGRAM', _('Program / Show')

    title_ar = models.CharField(max_length=200)
    title_en = models.CharField(max_length=200, blank=True)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    media_type = models.CharField(max_length=15, choices=MediaType.choices, default=MediaType.MOVIE, db_index=True)
    release_date = models.DateField(null=True, blank=True)
    poster_url = models.URLField(blank=True, validators=[URLValidator(schemes=['http', 'https'])])
    synopsis = models.TextField(blank=True)
    rating = models.DecimalField(
        max_digits=3, decimal_places=1, null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
    )

    # Commercial-only attributes; left blank for every other media_type.
    advertiser_company = models.CharField(max_length=200, blank=True)
    brand_name = models.CharField(max_length=200, blank=True)
    campaign_concept = models.TextField(blank=True)

    links = GenericRelation(ExternalLink)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-release_date', 'title_ar')
        indexes = [
            models.Index(fields=['media_type']),
            models.Index(fields=['release_date']),
            models.Index(fields=['slug']),
            models.Index(fields=['visibility']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title_en or self.title_ar, allow_unicode=True)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.title_ar} ({self.get_media_type_display()})'


class MediaCredit(models.Model):
    class Role(models.TextChoices):
        DIRECTOR = 'DIRECTOR', _('Director')
        PRODUCER = 'PRODUCER', _('Producer')
        SCREENWRITER = 'SCREENWRITER', _('Screenwriter')
        CINEMATOGRAPHER = 'CINEMATOGRAPHER', _('Cinematographer')
        COMPOSER = 'COMPOSER', _('Composer')
        ACTOR = 'ACTOR', _('Actor')
        OTHER = 'OTHER', _('Other')

    media = models.ForeignKey(Media, on_delete=models.CASCADE, related_name='credits')
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='media_credits')
    role = models.CharField(max_length=20, choices=Role.choices, db_index=True)
    character_name = models.CharField(max_length=150, blank=True)

    class Meta:
        unique_together = ('media', 'person', 'role', 'character_name')

    def __str__(self):
        return f'{self.person} - {self.role} - {self.media}'
