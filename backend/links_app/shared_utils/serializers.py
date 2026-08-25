def serialize_link(link):
    return {
        'id': link.id,
        'platform': link.platform.platform_name,
        'platform_label': link.platform.get_platform_name_display(),
        'direct_url': link.direct_url,
        'embed_code': link.embed_code,
        'access_type': link.access_type,
    }


def serialize_publishable(obj):
    return {
        'visibility': obj.visibility,
        'visibility_label': obj.get_visibility_display(),
        'publish_at': obj.publish_at,
        'is_live': obj.is_live,
    }
