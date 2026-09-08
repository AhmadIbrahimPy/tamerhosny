"""Same-origin proxy for externally-hosted cover art (e.g. imported
records whose Song/Album.cover_art_url points at a third-party CDN like
Anghami's, which sends no Access-Control-Allow-Origin header).

Drawing such an image onto a <canvas> (the shareable win/recap card
images - see static/website/js/share-card.js) needs it either same-
origin or served with CORS headers, or the browser refuses to load it
at all (crossOrigin='anonymous') or taints the canvas so toBlob()/
toDataURL() throw a SecurityError (no crossOrigin set). Fetching it
server-side and handing it back from our own domain sidesteps both.

Deliberately NOT a general-purpose open proxy: only a URL that already
matches an existing Song/Album.cover_art_url in our own catalog is
proxied, closing off SSRF (hitting arbitrary/internal URLs through our
server) that an unrestricted "fetch whatever URL you give me" endpoint
would otherwise allow.
"""
import urllib.request

from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.views.decorators.http import require_GET

from backend.music_app.models import Album, Song


@require_GET
def cover_art_proxy(request):
    url = request.GET.get('url', '').strip()
    if not url:
        return HttpResponseBadRequest('missing url')

    is_known_cover = (
        Song.objects.filter(cover_art_url=url).exists()
        or Album.objects.filter(cover_art_url=url).exists()
    )
    if not is_known_cover:
        return HttpResponseNotFound()

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as upstream:
            content = upstream.read()
            content_type = upstream.headers.get('Content-Type') or 'image/jpeg'
    except Exception:
        return HttpResponseNotFound()

    response = HttpResponse(content, content_type=content_type)
    response['Cache-Control'] = 'public, max-age=86400'
    return response
