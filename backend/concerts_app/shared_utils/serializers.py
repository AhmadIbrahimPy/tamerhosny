from backend.links_app.shared_utils.serializers import serialize_link, serialize_publishable


def serialize_concert(concert, request=None):
    return {
        'id': concert.id,
        'title_ar': concert.title_ar,
        'title_en': concert.title_en,
        'slug': concert.slug,
        'status': concert.status,
        'is_upcoming': concert.is_upcoming,
        'date': concert.date,
        'venue_name': concert.venue_name,
        'city': concert.city,
        'country': concert.country,
        'description': concert.description,
        'poster_url': concert.poster_url,
        'organizer': {'id': concert.organizer_id, 'name': concert.organizer.name} if concert.organizer_id else None,
        'links': [serialize_link(link) for link in concert.links.select_related('platform').all()],
        **serialize_publishable(concert),
    }
