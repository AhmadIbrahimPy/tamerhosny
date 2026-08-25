from rest_framework import status

from backend.links_app.shared_utils.dates import parse_datetime_field
from backend.music_app.models import Album
from backend.music_app.shared_utils.serializers import serialize_album


class AlbumsHandle:
    def __init__(self, request):
        self.request = request

    def all(self):
        albums = Album.objects.select_related('record_label').all()
        if not getattr(self.request, 'user', None) or not self.request.user.is_authenticated:
            albums = Album.visible_queryset(albums)
        data = [serialize_album(album, self.request) for album in albums]
        return status.HTTP_200_OK, 'Albums fetched successfully.', {'albums': data}

    def view(self, pk):
        album = Album.objects.select_related('record_label').filter(pk=pk).first()
        if not album:
            return status.HTTP_404_NOT_FOUND, 'Album not found.', None
        return status.HTTP_200_OK, 'Album fetched successfully.', {'album': serialize_album(album, self.request)}

    def create(self):
        title_ar = self.request.data.get('title_ar')
        if not title_ar:
            return status.HTTP_400_BAD_REQUEST, 'title_ar is required.', None

        album = Album.objects.create(
            title_ar=title_ar,
            title_en=self.request.data.get('title_en', ''),
            release_date=self.request.data.get('release_date'),
            cover_art_url=self.request.data.get('cover_art_url', ''),
            record_label_id=self.request.data.get('record_label_id'),
            visibility=self.request.data.get('visibility', Album.Visibility.PUBLISHED),
            publish_at=parse_datetime_field(self.request.data.get('publish_at')),
        )
        return status.HTTP_201_CREATED, 'Album created successfully.', {'album': serialize_album(album, self.request)}

    def update(self, pk):
        album = Album.objects.filter(pk=pk).first()
        if not album:
            return status.HTTP_404_NOT_FOUND, 'Album not found.', None

        for field in (
            'title_ar', 'title_en', 'release_date', 'cover_art_url', 'record_label_id', 'visibility',
        ):
            if field in self.request.data:
                setattr(album, field, self.request.data[field])
        if 'publish_at' in self.request.data:
            album.publish_at = parse_datetime_field(self.request.data.get('publish_at'))
        album.save()

        return status.HTTP_200_OK, 'Album updated successfully.', {'album': serialize_album(album, self.request)}

    def delete(self, pk):
        album = Album.objects.filter(pk=pk).first()
        if not album:
            return status.HTTP_404_NOT_FOUND, 'Album not found.', None
        album.delete()
        return status.HTTP_200_OK, 'Album deleted successfully.', None
