from django.conf import settings


def vapid_public_key(request):
    """Exposes the Web Push public key to every website template (used
    by base.html's push-notification script) - empty when VAPID isn't
    configured, which the {% if %} around that script treats as "feature
    off" rather than an error.
    """
    return {'VAPID_PUBLIC_KEY': settings.VAPID_PUBLIC_KEY}
