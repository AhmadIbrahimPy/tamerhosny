from django.conf import settings


def vapid_public_key(request):
    """Exposes the Web Push public key to every website template (used
    by base.html's push-notification script) - empty when VAPID isn't
    configured, which the {% if %} around that script treats as "feature
    off" rather than an error.
    """
    return {'VAPID_PUBLIC_KEY': settings.VAPID_PUBLIC_KEY}


def maptiler_api_key(request):
    """Exposes the MapTiler tile key to every template (dashboard's
    concert location picker + the public concert page's map) - empty
    when unconfigured, which the {% if %} around each map treats as
    "show the plain fallback" rather than a broken/watermarked map.
    """
    return {'MAPTILER_API_KEY': settings.MAPTILER_API_KEY}


def tamer_photo_url(request):
    """Exposes Tamer Hosny's own profile photo to every template - every
    duet card site-wide (my-duets, a song's duets list, a public
    profile, "غنى فلان مع تامر" sliders...) needs it alongside the
    duet's own singer photo for the mini-player's two-avatar thumbnail,
    so this saves each of those views its own near-identical Person
    lookup. Cached process-wide since it basically never changes and
    every page load would otherwise cost an extra query.
    """
    from django.core.cache import cache

    cached = cache.get('tamer_photo_url', default='__unset__')
    if cached != '__unset__':
        return {'TAMER_PHOTO_URL': cached}

    from backend.people_app.models import Person

    tamer = Person.objects.filter(slug='tamer-hosny').first()
    url = tamer.profile_image.url if tamer and tamer.profile_image else ''
    cache.set('tamer_photo_url', url, 3600)
    return {'TAMER_PHOTO_URL': url}
