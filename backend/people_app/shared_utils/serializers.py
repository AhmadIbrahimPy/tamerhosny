def serialize_person(person, request=None):
    photo_url = person.photo.url if person.photo else None
    if photo_url and request:
        photo_url = request.build_absolute_uri(photo_url)
    return {
        'id': person.id,
        'name': person.name,
        'slug': person.slug,
        'bio': person.bio,
        'photo': photo_url,
    }
