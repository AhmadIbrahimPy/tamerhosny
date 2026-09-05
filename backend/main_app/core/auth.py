from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from backend.main_app.models import LoginSession
from backend.main_app.shared_utils.login_sessions import record_login_session


class AuthHandle:
    def __init__(self, request):
        self.request = request

    def login(self):
        username = self.request.data.get('username')
        password = self.request.data.get('password')
        if not username or not password:
            return status.HTTP_400_BAD_REQUEST, 'username and password are required.', None

        user = authenticate(self.request, username=username, password=password)
        if not user or not user.is_active:
            return status.HTTP_401_UNAUTHORIZED, 'Invalid credentials.', None

        record_login_session(self.request, user, LoginSession.Source.APP)

        refresh = RefreshToken.for_user(user)
        data = {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {'id': user.id, 'username': user.username, 'role': user.role},
        }
        return status.HTTP_200_OK, 'Logged in successfully.', data

    def refresh(self):
        raw_refresh = self.request.data.get('refresh')
        if not raw_refresh:
            return status.HTTP_400_BAD_REQUEST, 'refresh token is required.', None

        try:
            refresh = RefreshToken(raw_refresh)
        except Exception:
            return status.HTTP_401_UNAUTHORIZED, 'Refresh token is invalid or expired.', None

        return status.HTTP_200_OK, 'Token refreshed.', {'access': str(refresh.access_token)}

    def logout(self):
        raw_refresh = self.request.data.get('refresh')
        if not raw_refresh:
            return status.HTTP_400_BAD_REQUEST, 'refresh token is required.', None

        try:
            RefreshToken(raw_refresh).blacklist()
        except Exception:
            pass

        return status.HTTP_200_OK, 'Logged out successfully.', None
