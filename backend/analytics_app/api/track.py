from rest_framework.response import Response
from rest_framework.views import APIView

from backend.analytics_app.core.track import TrackHandle


class TrackAPIView(APIView):
    """Public, unauthenticated endpoint the website calls to record a
    view/play/share/external-click. No auth: any visitor can send these.
    """

    def post(self, request, **kwargs):
        call_response = TrackHandle(request).create()
        return Response({'details': call_response[1], 'data': call_response[2]}, call_response[0])
