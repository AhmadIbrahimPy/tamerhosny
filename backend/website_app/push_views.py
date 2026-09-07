"""Web Push subscription endpoints for the public site, plus serving the
service worker from the site root (its scope defaults to the directory
of its own URL, so it can't be served from under /static/ without also
sending Service-Worker-Allowed - simplest is a dedicated root route,
same idea as website_app.views.robots_txt).
"""
import json
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from backend.main_app.models import PushSubscription

SW_PATH = Path(settings.BASE_DIR) / 'static' / 'website' / 'js' / 'sw.js'


@require_GET
def service_worker(request):
    return HttpResponse(
        SW_PATH.read_text(encoding='utf-8'),
        content_type='application/javascript',
        headers={'Service-Worker-Allowed': '/'},
    )


def _json_body(request):
    try:
        return json.loads(request.body or '{}')
    except (ValueError, TypeError):
        return {}


@csrf_exempt
@require_POST
def push_subscribe(request):
    data = _json_body(request)
    endpoint = (data.get('endpoint') or '').strip()
    keys = data.get('keys') or {}
    p256dh = keys.get('p256dh')
    auth = keys.get('auth')

    if not endpoint or not p256dh or not auth:
        return JsonResponse({'status': 'error', 'message': 'invalid subscription'}, status=400)

    user = request.user if request.user.is_authenticated else None
    PushSubscription.objects.update_or_create(
        endpoint=endpoint, defaults={'p256dh': p256dh, 'auth': auth, 'user': user},
    )
    return JsonResponse({'status': 'success'})


@csrf_exempt
@require_POST
def push_unsubscribe(request):
    endpoint = (_json_body(request).get('endpoint') or '').strip()
    if endpoint:
        PushSubscription.objects.filter(endpoint=endpoint).delete()
    return JsonResponse({'status': 'success'})
