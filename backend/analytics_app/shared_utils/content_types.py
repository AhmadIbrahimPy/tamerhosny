from django.contrib.contenttypes.models import ContentType

# Public-facing "kind" strings the website sends, mapped to the real
# app_label/model pair. Keeps the tracking API from having to expose
# Django's internal app_label.model naming.
KIND_TO_MODEL = {
    'person': ('people_app', 'person'),
    'studio': ('studios_app', 'studio'),
    'album': ('music_app', 'album'),
    'song': ('music_app', 'song'),
    'media': ('media_app', 'media'),
    'concert': ('concerts_app', 'concert'),
    'ad': ('ads_app', 'advertisement'),
}

def content_type_for_kind(kind):
    mapping = KIND_TO_MODEL.get(kind)
    if not mapping:
        return None
    app_label, model = mapping
    return ContentType.objects.get_by_natural_key(app_label, model)
