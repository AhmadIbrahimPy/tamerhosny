"""Web Push notifications - reaches a subscribed browser even when it's
closed (the OS/browser's own push service wakes the service worker),
which is the whole point over anything that only works while a tab is
open. No per-vendor SDK/API key needed: VAPID (see settings.VAPID_*)
identifies this site to whichever push service the browser uses.

Triggers that actually send one live in their own apps (see the
post_save signals on Song/Album/SongLyricSegment/ExternalLink, and the
send_daily_guess_reminder Celery task) - this module only knows how to
deliver a payload to whoever is subscribed.
"""
import json
import logging

from django.conf import settings
from pywebpush import WebPushException, webpush

from backend.main_app.models import PushSubscription

logger = logging.getLogger(__name__)


def _send_to_subscription(subscription, payload):
    """Delivers to one subscription; deletes it if the push service says
    it's gone (410/404 - the browser uninstalled, cleared site data, or
    the endpoint otherwise expired), which is the normal, expected way
    for these to go stale over time, not an error worth logging.
    """
    try:
        webpush(
            subscription_info={
                'endpoint': subscription.endpoint,
                'keys': {'p256dh': subscription.p256dh, 'auth': subscription.auth},
            },
            data=json.dumps(payload),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={'sub': f'mailto:{settings.VAPID_CLAIM_EMAIL}'},
            ttl=60 * 60 * 24,
        )
    except WebPushException as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        if status_code in (404, 410):
            subscription.delete()
        else:
            logger.warning('Web push failed for subscription %s: %s', subscription.pk, exc)


def _build_payload(title, body, url):
    return {
        'title': title,
        'body': body,
        'url': url or '/',
        'icon': '/static/images/logos/icon.jpeg',
    }


def send_push_to_user(user, title, body, url=None):
    """One user's own subscription(s) - the daily "خمّن الأغنية" reminder,
    or anything else meant for a specific person rather than everyone.
    """
    if not settings.VAPID_PRIVATE_KEY:
        return
    payload = _build_payload(title, body, url)
    for subscription in PushSubscription.objects.filter(user=user):
        _send_to_subscription(subscription, payload)


def send_push_to_all(title, body, url=None):
    """Every subscribed browser, logged in or not - new song/album drops,
    or a song gaining audio/lyrics/platform links, are things any visitor
    would want to know about, not just accounts with a UserGameProfile.
    """
    if not settings.VAPID_PRIVATE_KEY:
        return
    payload = _build_payload(title, body, url)
    for subscription in PushSubscription.objects.all().iterator():
        _send_to_subscription(subscription, payload)
