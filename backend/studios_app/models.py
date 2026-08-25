from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class Studio(models.Model):
    class EntityType(models.TextChoices):
        RECORDING_STUDIO = 'RECORDING_STUDIO', _('Recording Studio')
        RECORD_LABEL = 'RECORD_LABEL', _('Record Label')
        PRODUCTION_COMPANY = 'PRODUCTION_COMPANY', _('Production Company')
        DISTRIBUTION = 'DISTRIBUTION', _('Distribution')

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    entity_type = models.CharField(
        max_length=25, choices=EntityType.choices, default=EntityType.RECORDING_STUDIO, db_index=True,
    )
    logo = models.ImageField(upload_to='studios/logos/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('name',)
        indexes = [models.Index(fields=['entity_type'])]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} ({self.get_entity_type_display()})'
