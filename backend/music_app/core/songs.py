from rest_framework import status

from backend.links_app.core.links import sync_links
from backend.music_app.models import Song, SongCredit
from backend.music_app.shared_utils.serializers import serialize_song


class SongsHandle:
    def __init__(self, request):
        self.request = request

    def all(self):
        queryset = Song.objects.select_related('album', 'recording_studio', 'related_media')
        song_type = self.request.query_params.get('song_type')
        if song_type:
            queryset = queryset.filter(song_type=song_type)
        data = [serialize_song(song, self.request) for song in queryset]
        return status.HTTP_200_OK, 'Songs fetched successfully.', {'songs': data}

    def view(self, pk):
        song = Song.objects.select_related('album', 'recording_studio', 'related_media').filter(pk=pk).first()
        if not song:
            return status.HTTP_404_NOT_FOUND, 'Song not found.', None
        return status.HTTP_200_OK, 'Song fetched successfully.', {'song': serialize_song(song, self.request)}

    def create(self):
        title_ar = self.request.data.get('title_ar')
        song_type = self.request.data.get('song_type')
        if not title_ar or song_type not in Song.SongType.values:
            return status.HTTP_400_BAD_REQUEST, 'title_ar and a valid song_type are required.', None

        song = Song.objects.create(
            title_ar=title_ar,
            title_en=self.request.data.get('title_en', ''),
            song_type=song_type,
            duration_seconds=self.request.data.get('duration_seconds'),
            lyrics=self.request.data.get('lyrics', ''),
            release_year=self.request.data.get('release_year'),
            is_duet=self.request.data.get('is_duet', False),
            recording_studio_id=self.request.data.get('recording_studio_id'),
            album_id=self.request.data.get('album_id'),
            related_media_id=self.request.data.get('related_media_id'),
        )
        sync_links(song, self.request.data.get('links'))
        self._sync_credits(song, self.request.data.get('credits'))
        return status.HTTP_201_CREATED, 'Song created successfully.', {'song': serialize_song(song, self.request)}

    def update(self, pk):
        song = Song.objects.filter(pk=pk).first()
        if not song:
            return status.HTTP_404_NOT_FOUND, 'Song not found.', None

        for field in (
            'title_ar', 'title_en', 'song_type', 'duration_seconds', 'lyrics', 'release_year',
            'is_duet', 'recording_studio_id', 'album_id', 'related_media_id',
        ):
            if field in self.request.data:
                setattr(song, field, self.request.data[field])
        song.save()

        if 'links' in self.request.data:
            sync_links(song, self.request.data.get('links'))
        if 'credits' in self.request.data:
            self._sync_credits(song, self.request.data.get('credits'))

        return status.HTTP_200_OK, 'Song updated successfully.', {'song': serialize_song(song, self.request)}

    def delete(self, pk):
        song = Song.objects.filter(pk=pk).first()
        if not song:
            return status.HTTP_404_NOT_FOUND, 'Song not found.', None
        song.delete()
        return status.HTTP_200_OK, 'Song deleted successfully.', None

    @staticmethod
    def _sync_credits(song, credits_data):
        song.credits.all().delete()
        SongCredit.objects.bulk_create([
            SongCredit(song=song, person_id=item['person_id'], role=item['role'])
            for item in credits_data or []
            if item.get('person_id') and item.get('role')
        ])
