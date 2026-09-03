from backend.links_app.shared_utils.serializers import serialize_link, serialize_publishable


def serialize_album(album, request=None):
    cover_url = album.cover_image.url if album.cover_image else None
    if cover_url and request:
        cover_url = request.build_absolute_uri(cover_url)

    return {
        'id': album.id,
        'title_ar': album.title_ar,
        'title_en': album.title_en,
        'slug': album.slug,
        'release_date': album.release_date,
        'cover_image': cover_url,
        'cover_art_url': album.cover_art_url,
        'record_label': {'id': album.record_label_id, 'name': album.record_label.name} if album.record_label_id else None,
        **serialize_publishable(album),
    }


def serialize_song(song, request=None):
    if song.cover_image:
        cover_url = song.cover_image.url
    elif song.album_id and song.album.cover_image:
        cover_url = song.album.cover_image.url
    else:
        cover_url = None
    if cover_url and request:
        cover_url = request.build_absolute_uri(cover_url)

    return {
        'id': song.id,
        'title_ar': song.title_ar,
        'title_en': song.title_en,
        'slug': song.slug,
        'cover_image': cover_url,
        'duration_seconds': song.duration_seconds,
        'lyrics': song.lyrics,
        'lyric_segments': [
            {
                'start_seconds': segment.start_seconds,
                'end_seconds': segment.end_seconds,
                'segment_type': segment.segment_type,
                'text': segment.text,
                'vocal_doubling': segment.vocal_doubling,
                'double_tracking': segment.double_tracking,
            }
            for segment in song.lyric_segments.all()
        ],
        'release_year': song.release_year,
        'song_type': song.song_type,
        'is_duet': song.is_duet,
        'has_audio': bool(song.audio_file),
        'recording_studio': (
            {'id': song.recording_studio_id, 'name': song.recording_studio.name}
            if song.recording_studio_id else None
        ),
        'album': {'id': song.album_id, 'title_ar': song.album.title_ar} if song.album_id else None,
        'related_media': (
            {'id': song.related_media_id, 'title_ar': song.related_media.title_ar}
            if song.related_media_id else None
        ),
        'links': [serialize_link(link) for link in song.links.select_related('platform').all()],
        'credits': [
            {'person_id': credit.person_id, 'person_name': credit.person.full_name_ar, 'role': credit.role}
            for credit in song.credits.select_related('person').all()
        ],
        'audio_bpm': song.audio_bpm,
        'audio_key': song.audio_key,
        'audio_mood': song.audio_mood,
        'audio_energy': song.audio_energy,
        'audio_danceability': song.audio_danceability,
        'audio_analysis_data': song.audio_analysis_data,
        **serialize_publishable(song),
    }
