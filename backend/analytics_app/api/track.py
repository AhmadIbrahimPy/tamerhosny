from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from backend.analytics_app.core.track import TrackHandle


@method_decorator(csrf_exempt, name='dispatch')
class TrackAPIView(APIView):
    """Public, unauthenticated endpoint the website calls to record a
    view/play/share/external-click. No auth: any visitor can send these.

    authentication_classes is cleared, not just permission_classes: DRF's
    SessionAuthentication runs its own CSRF check independently of the
    view's csrf_exempt decorator whenever the caller has a logged-in
    session, which was rejecting every track call from a signed-in user
    with 403 (the plain fetch() this comes from never sends a CSRF
    header, since the endpoint isn't meant to need one at all).
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, **kwargs):
        call_response = TrackHandle(request).create()
        return Response({'details': call_response[1], 'data': call_response[2]}, call_response[0])
