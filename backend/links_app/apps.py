from django.apps import AppConfig


class LinksAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.links_app'
    label = 'links_app'

    def ready(self):
        from backend.links_app import signals  # noqa: F401
