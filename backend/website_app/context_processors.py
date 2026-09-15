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
