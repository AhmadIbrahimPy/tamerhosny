from backend.links_app.shared_utils.serializers import serialize_link, serialize_publishable


def serialize_media(media, request=None):
    return {
        'id': media.id,
        'title_ar': media.title_ar,
        'title_en': media.title_en,
        'slug': media.slug,
        'media_type': media.media_type,
        'release_date': media.release_date,
        'poster_url': media.poster_url,
        'synopsis': media.synopsis,
        'rating': media.rating,
        'advertiser_company': media.advertiser_company,
        'brand_name': media.brand_name,
        'campaign_concept': media.campaign_concept,
        'links': [serialize_link(link) for link in media.links.select_related('platform').all()],
        'credits': [
            {
                'person_id': credit.person_id,
                'person_name': credit.person.full_name_ar,
                'role': credit.role,
                'character_name': credit.character_name,
            }
            for credit in media.credits.select_related('person').all()
        ],
        **serialize_publishable(media),
    }
