from rest_framework import status

from backend.analytics_app.models import AnalyticsEvent
from backend.analytics_app.shared_utils.content_types import content_type_for_kind
from backend.links_app.models import ExternalLink, Platform


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


class TrackHandle:
    def __init__(self, request):
        self.request = request

    def create(self):
        event_type = self.request.data.get('event_type')
        kind = self.request.data.get('content_type')
        object_id = self.request.data.get('object_id')

        if event_type not in AnalyticsEvent.EventType.values:
            return status.HTTP_400_BAD_REQUEST, 'event_type is invalid.', None
        content_type = content_type_for_kind(kind)
        if not content_type or not object_id:
            return status.HTTP_400_BAD_REQUEST, 'content_type and object_id are required.', None

        model_class = content_type.model_class()
        if not model_class.objects.filter(pk=object_id).exists():
            return status.HTTP_404_NOT_FOUND, 'Target object not found.', None

        platform = None
        external_link = None
        if event_type == AnalyticsEvent.EventType.EXTERNAL_CLICK:
            platform_name = self.request.data.get('platform')
            platform = Platform.objects.filter(platform_name=platform_name).first()
            link_id = self.request.data.get('external_link_id')
            if link_id:
                external_link = ExternalLink.objects.filter(pk=link_id).first()

        share_channel = ''
        if event_type == AnalyticsEvent.EventType.SHARE:
            share_channel = self.request.data.get('share_channel', '')
            if share_channel not in AnalyticsEvent.ShareChannel.values:
                share_channel = AnalyticsEvent.ShareChannel.OTHER

        AnalyticsEvent.objects.create(
            event_type=event_type,
            content_type=content_type,
            object_id=object_id,
            platform=platform,
            external_link=external_link,
            share_channel=share_channel,
            session_key=self.request.session.session_key or '',
            referrer=self.request.data.get('referrer', '')[:500],
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')[:255],
            ip_address=_client_ip(self.request),
        )
        return status.HTTP_201_CREATED, 'Event recorded.', None
