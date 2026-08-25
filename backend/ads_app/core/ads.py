from rest_framework import status

from backend.ads_app.models import Advertisement
from backend.ads_app.shared_utils.serializers import serialize_ad
from backend.analytics_app.shared_utils.content_types import content_type_for_kind


class AdsHandle:
    def __init__(self, request):
        self.request = request

    def all(self):
        queryset = Advertisement.objects.select_related('content_type').all()
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(is_active=True)
        placement = self.request.query_params.get('placement')
        if placement:
            queryset = [ad for ad in queryset if ad.shows_on(placement)]
        data = [serialize_ad(ad, self.request) for ad in queryset]
        return status.HTTP_200_OK, 'Ads fetched successfully.', {'ads': data}

    def view(self, pk):
        ad = Advertisement.objects.filter(pk=pk).first()
        if not ad:
            return status.HTTP_404_NOT_FOUND, 'Ad not found.', None
        return status.HTTP_200_OK, 'Ad fetched successfully.', {'ad': serialize_ad(ad, self.request)}

    def _apply_link(self, ad):
        kind = self.request.data.get('link_kind')
        object_id = self.request.data.get('link_object_id')
        if kind and object_id:
            content_type = content_type_for_kind(kind)
            if content_type:
                ad.content_type = content_type
                ad.object_id = object_id
        elif 'link_kind' in self.request.data:
            ad.content_type = None
            ad.object_id = None

    def create(self):
        title = self.request.data.get('title')
        if not title:
            return status.HTTP_400_BAD_REQUEST, 'title is required.', None

        ad = Advertisement(
            title=title,
            image=self.request.FILES.get('image'),
            is_active=self.request.data.get('is_active', True),
            external_url=self.request.data.get('external_url', ''),
            show_on_all_pages=self.request.data.get('show_on_all_pages', True),
            placements=self.request.data.get('placements', []),
        )
        self._apply_link(ad)
        ad.save()
        return status.HTTP_201_CREATED, 'Ad created successfully.', {'ad': serialize_ad(ad, self.request)}

    def update(self, pk):
        ad = Advertisement.objects.filter(pk=pk).first()
        if not ad:
            return status.HTTP_404_NOT_FOUND, 'Ad not found.', None

        for field in ('title', 'is_active', 'external_url', 'show_on_all_pages', 'placements'):
            if field in self.request.data:
                setattr(ad, field, self.request.data[field])
        if self.request.FILES.get('image'):
            ad.image = self.request.FILES['image']
        self._apply_link(ad)
        ad.save()
        return status.HTTP_200_OK, 'Ad updated successfully.', {'ad': serialize_ad(ad, self.request)}

    def delete(self, pk):
        ad = Advertisement.objects.filter(pk=pk).first()
        if not ad:
            return status.HTTP_404_NOT_FOUND, 'Ad not found.', None
        ad.delete()
        return status.HTTP_200_OK, 'Ad deleted successfully.', None
