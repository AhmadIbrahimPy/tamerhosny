from rest_framework.response import Response
from rest_framework.views import APIView

from backend.main_app.core.auth import AuthHandle


class LoginAPIView(APIView):
    def post(self, request, **kwargs):
        call_response = AuthHandle(request).login()
        return Response({'details': call_response[1], 'data': call_response[2]}, call_response[0])


class RefreshAPIView(APIView):
    def post(self, request, **kwargs):
        call_response = AuthHandle(request).refresh()
        return Response({'details': call_response[1], 'data': call_response[2]}, call_response[0])


class LogoutAPIView(APIView):
    def post(self, request, **kwargs):
        call_response = AuthHandle(request).logout()
        return Response({'details': call_response[1], 'data': call_response[2]}, call_response[0])
