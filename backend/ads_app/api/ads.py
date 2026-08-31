from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from backend.ads_app.core.ads import AdsHandle
from backend.main_app.shared_utils.authentication_manager import UserAuthenticationManager


@method_decorator(csrf_exempt, name='dispatch')
class AdsAPIView(APIView):
    permission_classes = [AllowAny]

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get(self, request, pk=None, **kwargs):
        call_response = AdsHandle(request)
        call_response = call_response.view(pk) if pk else call_response.all()
        return Response({'details': call_response[1], 'data': call_response[2]}, call_response[0])

    def post(self, request, **kwargs):
        call_response = UserAuthenticationManager(request).handle_logged_in()
        if call_response[0] == status.HTTP_200_OK:
            call_response = AdsHandle(request).create()
        return Response({'details': call_response[1], 'data': call_response[2]}, call_response[0])

    def put(self, request, pk, **kwargs):
        call_response = UserAuthenticationManager(request).handle_logged_in()
        if call_response[0] == status.HTTP_200_OK:
            call_response = AdsHandle(request).update(pk)
        return Response({'details': call_response[1], 'data': call_response[2]}, call_response[0])

    def delete(self, request, pk, **kwargs):
        call_response = UserAuthenticationManager(request).handle_logged_in()
        if call_response[0] == status.HTTP_200_OK:
            call_response = AdsHandle(request).delete(pk)
        return Response({'details': call_response[1], 'data': call_response[2]}, call_response[0])
