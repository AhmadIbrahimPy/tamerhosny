from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils.translation import gettext_lazy as _

from backend.links_app.models import ExternalLink
from backend.main_app.shared_utils.slugs import generate_ascii_slug


class Person(models.Model):
    class Role(models.TextChoices):
        SINGER = 'SINGER', _('Singer')
        POET = 'POET', _('Poet / Lyricist')
        COMPOSER = 'COMPOSER', _('Composer')
        ARRANGER = 'ARRANGER', _('Arranger')
        MUSIC_PRODUCER = 'MUSIC_PRODUCER', _('Music Producer')
        RECORDING_ENGINEER = 'RECORDING_ENGINEER', _('Recording Engineer')
        MIXING_ENGINEER = 'MIXING_ENGINEER', _('Mixing Engineer')
        MASTERING_ENGINEER = 'MASTERING_ENGINEER', _('Mastering Engineer')
        MIX_MASTER_ENGINEER = 'MIX_MASTER_ENGINEER', _('Mix & Master Engineer')
        DIRECTOR = 'DIRECTOR', _('Director')
        PRODUCER = 'PRODUCER', _('Producer')
        SCREENWRITER = 'SCREENWRITER', _('Screenwriter')
        CINEMATOGRAPHER = 'CINEMATOGRAPHER', _('Cinematographer')
        ACTOR = 'ACTOR', _('Actor')
        CO_ARTIST = 'CO_ARTIST', _('Co-Artist / Featured Artist')
        OTHER = 'OTHER', _('Other')

    full_name_ar = models.CharField(max_length=200)
    full_name_en = models.CharField(max_length=200, blank=True)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    primary_role = models.CharField(max_length=30, choices=Role.choices, default=Role.OTHER, db_index=True)
    bio = models.TextField(blank=True)
    profile_image = models.ImageField(upload_to='people/', blank=True, null=True)
    links = GenericRelation(ExternalLink)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('full_name_ar',)
        indexes = [
            models.Index(fields=['primary_role']),
            models.Index(fields=['slug']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_ascii_slug(Person, self.full_name_en, 'person')
        super().save(*args, **kwargs)

    def __str__(self):
        return self.full_name_ar or self.full_name_en
