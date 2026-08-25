def serialize_person(person, request=None):
    photo_url = person.profile_image.url if person.profile_image else None
    if photo_url and request:
        photo_url = request.build_absolute_uri(photo_url)
    return {
        'id': person.id,
        'full_name_ar': person.full_name_ar,
        'full_name_en': person.full_name_en,
        'slug': person.slug,
        'primary_role': person.primary_role,
        'bio': person.bio,
        'profile_image': photo_url,
    }
