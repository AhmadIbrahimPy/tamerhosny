from backend.links_app.models import ExternalLink, Platform


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
