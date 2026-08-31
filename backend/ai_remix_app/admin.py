from django.contrib import admin
from .models import AudioSource, RemixProject, RemixSource, RemixOutput, AIModel


@admin.register(AudioSource)
class AudioSourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'source_type', 'bpm', 'key', 'duration', 'uploaded_at']
    list_filter = ['source_type', 'uploaded_at']
    search_fields = ['name']
    readonly_fields = ['uploaded_at']


@admin.register(RemixProject)
class RemixProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'target_bpm', 'target_key', 'created_at', 'updated_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(RemixSource)
class RemixSourceAdmin(admin.ModelAdmin):
    list_display = ['project', 'audio_source', 'volume', 'order', 'is_loop']
    list_filter = ['project', 'is_loop']
    search_fields = ['project__name', 'audio_source__name']


@admin.register(RemixOutput)
class RemixOutputAdmin(admin.ModelAdmin):
    list_display = ['project', 'format', 'bitrate', 'duration', 'file_size', 'created_at']
    list_filter = ['format', 'created_at']
    readonly_fields = ['created_at', 'duration', 'file_size']


@admin.register(AIModel)
class AIModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'version', 'model_type', 'is_active', 'created_at']
    list_filter = ['is_active', 'model_type', 'created_at']
    search_fields = ['name', 'version']
    readonly_fields = ['created_at']
