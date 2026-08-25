from rest_framework import status

from backend.concerts_app.models import Concert
from backend.concerts_app.shared_utils.serializers import serialize_concert
from backend.links_app.core.links import sync_links
from backend.links_app.shared_utils.dates import parse_datetime_field as _parse_date


class ConcertsHandle:
    def __init__(self, request):
        self.request = request

    def all(self):
        queryset = Concert.objects.select_related('organizer').all()
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if not self.request.user.is_authenticated:
            queryset = Concert.visible_queryset(queryset)
        data = [serialize_concert(concert, self.request) for concert in queryset]
        return status.HTTP_200_OK, 'Concerts fetched successfully.', {'concerts': data}

    def view(self, pk):
        concert = Concert.objects.select_related('organizer').filter(pk=pk).first()
        if not concert:
            return status.HTTP_404_NOT_FOUND, 'Concert not found.', None
        return status.HTTP_200_OK, 'Concert fetched successfully.', {'concert': serialize_concert(concert, self.request)}

    def create(self):
        title_ar = self.request.data.get('title_ar')
        if not title_ar:
            return status.HTTP_400_BAD_REQUEST, 'title_ar is required.', None

        concert = Concert.objects.create(
            title_ar=title_ar,
            title_en=self.request.data.get('title_en', ''),
            status=self.request.data.get('status', Concert.Status.UPCOMING),
            date=_parse_date(self.request.data.get('date')),
            venue_name=self.request.data.get('venue_name', ''),
            city=self.request.data.get('city', ''),
            country=self.request.data.get('country', ''),
            description=self.request.data.get('description', ''),
            poster_url=self.request.data.get('poster_url', ''),
            organizer_id=self.request.data.get('organizer_id'),
            visibility=self.request.data.get('visibility', Concert.Visibility.PUBLISHED),
            publish_at=_parse_date(self.request.data.get('publish_at')),
        )
        sync_links(concert, self.request.data.get('links'))
        return status.HTTP_201_CREATED, 'Concert created successfully.', {'concert': serialize_concert(concert, self.request)}

    def update(self, pk):
        concert = Concert.objects.filter(pk=pk).first()
        if not concert:
            return status.HTTP_404_NOT_FOUND, 'Concert not found.', None

        for field in (
            'title_ar', 'title_en', 'status', 'venue_name', 'city', 'country',
            'description', 'poster_url', 'organizer_id', 'visibility',
        ):
            if field in self.request.data:
                setattr(concert, field, self.request.data[field])
        if 'date' in self.request.data:
            concert.date = _parse_date(self.request.data.get('date'))
        if 'publish_at' in self.request.data:
            concert.publish_at = _parse_date(self.request.data.get('publish_at'))
        concert.save()

        if 'links' in self.request.data:
            sync_links(concert, self.request.data.get('links'))

        return status.HTTP_200_OK, 'Concert updated successfully.', {'concert': serialize_concert(concert, self.request)}

    def delete(self, pk):
        concert = Concert.objects.filter(pk=pk).first()
        if not concert:
            return status.HTTP_404_NOT_FOUND, 'Concert not found.', None
        concert.delete()
        return status.HTTP_200_OK, 'Concert deleted successfully.', None
