from django.contrib.contenttypes.models import ContentType

from backend.links_app.models import ExternalLink, Platform

# A one-off management command (link_songs_to_platforms) bulk-seeded
# every song with links built from its own slug rather than real
# streaming-platform URLs - e.g. https://open.spotify.com/track/<slug>.
# Those are indistinguishable from real links by platform/access_type
# alone, so the only reliable signature is the URL ending in the
# song's own slug right after one of these platform path prefixes.
_FAKE_SONG_LINK_PREFIXES = (
    'open.spotify.com/track/',
    'play.anghami.com/song/',
    'music.apple.com/album/',
    'youtube.com/watch?v=',
)


def delete_fake_song_platform_links(song):
    """Remove any still-lingering seeded placeholder links for this song
    (see _FAKE_SONG_LINK_PREFIXES) so it correctly shows up as missing
    platforms instead of looking already-linked. Safe to call on every
    view of the song - a no-op once the real/no links are in place.
    """
    if not song.slug:
        return
    content_type = ContentType.objects.get_for_model(song.__class__)
    links = ExternalLink.objects.filter(content_type=content_type, object_id=song.pk)
    fake_ids = [
        link.pk for link in links
        if link.direct_url.endswith(song.slug)
        and any(prefix in link.direct_url for prefix in _FAKE_SONG_LINK_PREFIXES)
    ]
    if fake_ids:
        ExternalLink.objects.filter(pk__in=fake_ids).delete()


def sync_links(content_object, links_data):
    """Replace all external links attached to content_object with the
    given list of {platform, direct_url, embed_code, access_type} dicts.
    Used internally by the music/media/concerts core handlers, not
    exposed as its own endpoint.
    """
    ExternalLink.objects.filter(
        content_type__model=content_object._meta.model_name,
        object_id=content_object.pk,
    ).delete()

    links = []
    for item in links_data or []:
        if not item.get('direct_url') or not item.get('platform'):
            continue
        platform, _ = Platform.objects.get_or_create(platform_name=item['platform'])
        links.append(ExternalLink(
            content_object=content_object,
            platform=platform,
            direct_url=item['direct_url'],
            embed_code=item.get('embed_code', ''),
            access_type=item.get('access_type', ExternalLink.AccessType.FREE),
        ))
    ExternalLink.objects.bulk_create(links)
