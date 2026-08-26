from django.contrib.contenttypes.fields import GenericRelation
from django.core.validators import MaxValueValidator, MinValueValidator, URLValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from backend.links_app.models import ExternalLink, HeroMediaMixin, PublishableModel
from backend.main_app.shared_utils.slugs import generate_ascii_slug
from backend.people_app.models import Person


class Media(PublishableModel, HeroMediaMixin):
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
    poster_image = models.ImageField(upload_to='media/posters/', blank=True, null=True)
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
            self.slug = generate_ascii_slug(Media, self.title_en, 'media')
        super().save(*args, **kwargs)

    @property
    def display_poster_url(self):
        if self.poster_image:
            return self.poster_image.url
        return self.poster_url

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


class CinemaVenue(models.Model):
    """A physical cinema (e.g. 'Mahatet Al Raml', 'Manshia'), managed once
    in a shared master list — like Platform — instead of retyping the same
    cinema's name/city on every movie it screens.
    """

    name = models.CharField(max_length=200, unique=True)
    city = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ('city', 'name')

    def __str__(self):
        return f'{self.name} ({self.city})' if self.city else self.name


class CinemaScreening(models.Model):
    """Links a movie to one of the shared cinema venues, with per-movie
    details (ticket price, booking link).
    """

    media = models.ForeignKey(Media, on_delete=models.CASCADE, related_name='screenings')
    venue = models.ForeignKey(CinemaVenue, on_delete=models.CASCADE, related_name='screenings')
    ticket_price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    booking_url = models.URLField(blank=True, validators=[URLValidator(schemes=['http', 'https'])])

    class Meta:
        unique_together = ('media', 'venue')
        ordering = ('venue__city', 'venue__name')

    def __str__(self):
        return f'{self.venue} - {self.media}'
