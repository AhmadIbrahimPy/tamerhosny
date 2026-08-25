from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.main_app.shared_utils.authentication_manager import UserAuthenticationManager
from backend.people_app.core.people import PeopleHandle


class PeopleAPIView(APIView):
    """GET is public (used by the public catalog site). Mutations require
    a dashboard-authenticated user.
    """

    def get(self, request, pk=None, **kwargs):
        call_response = PeopleHandle(request)
        call_response = call_response.view(pk) if pk else call_response.all()
        return Response({'details': call_response[1], 'data': call_response[2]}, call_response[0])

    def post(self, request, **kwargs):
        call_response = UserAuthenticationManager(request).handle_logged_in()
        if call_response[0] == status.HTTP_200_OK:
            call_response = PeopleHandle(request).create()
        return Response({'details': call_response[1], 'data': call_response[2]}, call_response[0])

    def put(self, request, pk, **kwargs):
        call_response = UserAuthenticationManager(request).handle_logged_in()
        if call_response[0] == status.HTTP_200_OK:
            call_response = PeopleHandle(request).update(pk)
        return Response({'details': call_response[1], 'data': call_response[2]}, call_response[0])

    def delete(self, request, pk, **kwargs):
        call_response = UserAuthenticationManager(request).handle_logged_in()
        if call_response[0] == status.HTTP_200_OK:
            call_response = PeopleHandle(request).delete(pk)
        return Response({'details': call_response[1], 'data': call_response[2]}, call_response[0])
