from django.db import models
from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext_lazy as _


class AudioSource(models.Model):
    """نموذج لتخزين الملفات الصوتية المصدر"""
    
    class SourceType(models.TextChoices):
        VOCAL = 'VOCAL', _('Vocal Track')
        INSTRUMENTAL = 'INSTRUMENTAL', _('Instrumental')
        DRUMS = 'DRUMS', _('Drums')
        BASS = 'BASS', _('Bass')
        OTHER = 'OTHER', _('Other')
    
    name = models.CharField(max_length=255, verbose_name=_('Source Name'))
    audio_file = models.FileField(
        upload_to='ai_remix/sources/',
        validators=[FileExtensionValidator(allowed_extensions=['mp3', 'wav', 'flac', 'm4a', 'ogg'])],
        verbose_name=_('Audio File')
    )
    source_type = models.CharField(
        max_length=20,
        choices=SourceType.choices,
        default=SourceType.OTHER,
        verbose_name=_('Source Type')
    )
    bpm = models.PositiveIntegerField(null=True, blank=True, verbose_name=_('BPM'))
    key = models.CharField(max_length=10, blank=True, verbose_name=_('Musical Key'))
    duration = models.FloatField(null=True, blank=True, verbose_name=_('Duration (seconds)'))
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Uploaded At'))
    
    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = _('Audio Source')
        verbose_name_plural = _('Audio Sources')
    
    def __str__(self):
        return self.name


class RemixProject(models.Model):
    """نموذج لمشروع الريمكس"""
    
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        PROCESSING = 'PROCESSING', _('Processing')
        COMPLETED = 'COMPLETED', _('Completed')
        FAILED = 'FAILED', _('Failed')
    
    name = models.CharField(max_length=255, verbose_name=_('Project Name'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name=_('Status')
    )
    target_bpm = models.PositiveIntegerField(null=True, blank=True, verbose_name=_('Target BPM'))
    target_key = models.CharField(max_length=10, blank=True, verbose_name=_('Target Key'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Remix Project')
        verbose_name_plural = _('Remix Projects')
    
    def __str__(self):
        return self.name


class RemixSource(models.Model):
    """ربط المصادر الصوتية بمشروع الريمكس"""
    
    project = models.ForeignKey(
        RemixProject,
        on_delete=models.CASCADE,
        related_name='sources',
        verbose_name=_('Project')
    )
    audio_source = models.ForeignKey(
        AudioSource,
        on_delete=models.CASCADE,
        related_name='remix_projects',
        verbose_name=_('Audio Source')
    )
    volume = models.FloatField(default=1.0, verbose_name=_('Volume'))
    start_time = models.FloatField(default=0.0, verbose_name=_('Start Time (seconds)'))
    end_time = models.FloatField(null=True, blank=True, verbose_name=_('End Time (seconds)'))
    is_loop = models.BooleanField(default=False, verbose_name=_('Loop'))
    fade_in = models.FloatField(default=0.0, verbose_name=_('Fade In (seconds)'))
    fade_out = models.FloatField(default=0.0, verbose_name=_('Fade Out (seconds)'))
    order = models.PositiveIntegerField(default=0, verbose_name=_('Order'))
    
    class Meta:
        ordering = ['order']
        verbose_name = _('Remix Source')
        verbose_name_plural = _('Remix Sources')
        unique_together = ['project', 'audio_source']
    
    def __str__(self):
        return f'{self.project.name} - {self.audio_source.name}'


class RemixOutput(models.Model):
    """نموذج لتخزين مخرجات الريمكس"""
    
    project = models.ForeignKey(
        RemixProject,
        on_delete=models.CASCADE,
        related_name='outputs',
        verbose_name=_('Project')
    )
    output_file = models.FileField(
        upload_to='ai_remix/outputs/',
        validators=[FileExtensionValidator(allowed_extensions=['mp3', 'wav', 'flac'])],
        verbose_name=_('Output File')
    )
    format = models.CharField(max_length=10, default='mp3', verbose_name=_('Format'))
    bitrate = models.CharField(max_length=10, default='320k', verbose_name=_('Bitrate'))
    sample_rate = models.PositiveIntegerField(default=44100, verbose_name=_('Sample Rate'))
    duration = models.FloatField(null=True, blank=True, verbose_name=_('Duration (seconds)'))
    file_size = models.BigIntegerField(null=True, blank=True, verbose_name=_('File Size (bytes)'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Remix Output')
        verbose_name_plural = _('Remix Outputs')
    
    def __str__(self):
        return f'{self.project.name} - {self.format}'


class AIModel(models.Model):
    """نموذج لتخزين معلومات نماذج الذكاء الاصطناعي"""
    
    name = models.CharField(max_length=255, unique=True, verbose_name=_('Model Name'))
    version = models.CharField(max_length=50, verbose_name=_('Version'))
    model_type = models.CharField(max_length=100, verbose_name=_('Model Type'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    model_path = models.CharField(max_length=500, verbose_name=_('Model Path'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('AI Model')
        verbose_name_plural = _('AI Models')
    
    def __str__(self):
        return f'{self.name} v{self.version}'
