def serialize_studio(studio, request=None):
    logo_url = studio.logo.url if studio.logo else None
    if logo_url and request:
        logo_url = request.build_absolute_uri(logo_url)
    return {
        'id': studio.id,
        'name': studio.name,
        'slug': studio.slug,
        'entity_type': studio.entity_type,
        'logo': logo_url,
    }
