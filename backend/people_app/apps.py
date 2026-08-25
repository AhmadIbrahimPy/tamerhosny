from django.apps import AppConfig


class PeopleAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.people_app'
    label = 'people_app'
