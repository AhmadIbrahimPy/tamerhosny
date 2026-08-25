from django.db import models
from django.utils.text import slugify


class Person(models.Model):
    class Role(models.TextChoices):
        SINGER = 'SINGER', 'Singer'
        POET = 'POET', 'Poet / Lyricist'
        COMPOSER = 'COMPOSER', 'Composer'
        ARRANGER = 'ARRANGER', 'Arranger'
        MUSIC_PRODUCER = 'MUSIC_PRODUCER', 'Music Producer'
        RECORDING_ENGINEER = 'RECORDING_ENGINEER', 'Recording Engineer'
        MIX_MASTER_ENGINEER = 'MIX_MASTER_ENGINEER', 'Mix & Master Engineer'
        DIRECTOR = 'DIRECTOR', 'Director'
        PRODUCER = 'PRODUCER', 'Producer'
        SCREENWRITER = 'SCREENWRITER', 'Screenwriter'
        CINEMATOGRAPHER = 'CINEMATOGRAPHER', 'Cinematographer'
        ACTOR = 'ACTOR', 'Actor'
        CO_ARTIST = 'CO_ARTIST', 'Co-Artist / Featured Artist'
        OTHER = 'OTHER', 'Other'

    full_name_ar = models.CharField(max_length=200)
    full_name_en = models.CharField(max_length=200, blank=True)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    primary_role = models.CharField(max_length=30, choices=Role.choices, db_index=True)
    bio = models.TextField(blank=True)
    profile_image = models.ImageField(upload_to='people/', blank=True, null=True)
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
            self.slug = slugify(self.full_name_en or self.full_name_ar, allow_unicode=True)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.full_name_ar or self.full_name_en
