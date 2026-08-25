def serialize_ad(ad, request=None):
    return {
        'id': ad.id,
        'title': ad.title,
        'image_url': request.build_absolute_uri(ad.image.url) if (ad.image and request) else (ad.image.url if ad.image else None),
        'is_active': ad.is_active,
        'show_on_all_pages': ad.show_on_all_pages,
        'placements': ad.placements,
        'linked_kind': ad.content_type.model if ad.content_type_id else None,
        'linked_object_id': ad.object_id,
        'external_url': ad.external_url,
        'target_url': ad.get_target_url(),
    }
