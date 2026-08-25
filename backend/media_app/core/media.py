from rest_framework import status

from backend.links_app.core.links import sync_links
from backend.links_app.shared_utils.dates import parse_datetime_field
from backend.media_app.models import Media, MediaCredit
from backend.media_app.shared_utils.serializers import serialize_media


class MediaHandle:
    def __init__(self, request):
        self.request = request

    def all(self):
        queryset = Media.objects.all()
        media_type = self.request.query_params.get('media_type')
        if media_type:
            queryset = queryset.filter(media_type=media_type)
        if not self.request.user.is_authenticated:
            queryset = Media.visible_queryset(queryset)
        data = [serialize_media(item, self.request) for item in queryset]
        return status.HTTP_200_OK, 'Media fetched successfully.', {'media': data}

    def view(self, pk):
        media = Media.objects.filter(pk=pk).first()
        if not media:
            return status.HTTP_404_NOT_FOUND, 'Media not found.', None
        return status.HTTP_200_OK, 'Media fetched successfully.', {'media': serialize_media(media, self.request)}

    def create(self):
        title_ar = self.request.data.get('title_ar')
        media_type = self.request.data.get('media_type')
        if not title_ar or media_type not in Media.MediaType.values:
            return status.HTTP_400_BAD_REQUEST, 'title_ar and a valid media_type are required.', None

        media = Media.objects.create(
            title_ar=title_ar,
            title_en=self.request.data.get('title_en', ''),
            media_type=media_type,
            release_date=self.request.data.get('release_date'),
            poster_url=self.request.data.get('poster_url', ''),
            synopsis=self.request.data.get('synopsis', ''),
            rating=self.request.data.get('rating'),
            advertiser_company=self.request.data.get('advertiser_company', ''),
            brand_name=self.request.data.get('brand_name', ''),
            campaign_concept=self.request.data.get('campaign_concept', ''),
            visibility=self.request.data.get('visibility', Media.Visibility.PUBLISHED),
            publish_at=parse_datetime_field(self.request.data.get('publish_at')),
        )
        sync_links(media, self.request.data.get('links'))
        self._sync_credits(media, self.request.data.get('credits'))
        return status.HTTP_201_CREATED, 'Media created successfully.', {'media': serialize_media(media, self.request)}

    def update(self, pk):
        media = Media.objects.filter(pk=pk).first()
        if not media:
            return status.HTTP_404_NOT_FOUND, 'Media not found.', None

        for field in (
            'title_ar', 'title_en', 'media_type', 'release_date', 'poster_url', 'synopsis',
            'rating', 'advertiser_company', 'brand_name', 'campaign_concept', 'visibility',
        ):
            if field in self.request.data:
                setattr(media, field, self.request.data[field])
        if 'publish_at' in self.request.data:
            media.publish_at = parse_datetime_field(self.request.data.get('publish_at'))
        media.save()

        if 'links' in self.request.data:
            sync_links(media, self.request.data.get('links'))
        if 'credits' in self.request.data:
            self._sync_credits(media, self.request.data.get('credits'))

        return status.HTTP_200_OK, 'Media updated successfully.', {'media': serialize_media(media, self.request)}

    def delete(self, pk):
        media = Media.objects.filter(pk=pk).first()
        if not media:
            return status.HTTP_404_NOT_FOUND, 'Media not found.', None
        media.delete()
        return status.HTTP_200_OK, 'Media deleted successfully.', None

    @staticmethod
    def _sync_credits(media, credits_data):
        media.credits.all().delete()
        MediaCredit.objects.bulk_create([
            MediaCredit(
                media=media,
                person_id=item['person_id'],
                role=item['role'],
                character_name=item.get('character_name', ''),
            )
            for item in credits_data or []
            if item.get('person_id') and item.get('role')
        ])
