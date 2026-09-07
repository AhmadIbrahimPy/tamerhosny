from django.apps import AppConfig


class MusicAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.music_app'
    label = 'music_app'

    def ready(self):
        from backend.music_app import signals  # noqa: F401
