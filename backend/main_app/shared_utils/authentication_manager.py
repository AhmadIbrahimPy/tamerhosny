from rest_framework import status
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from backend.main_app.models import UserAccount
from config.custom_packages.releases import check_version


class UserAuthenticationManager:
    """Single entry point every API view calls before delegating to a
    core Handle class. Always returns a (status, details, data) tuple.
    """

    def __init__(self, request):
        self.request = request

    def handle_logged_in(self, dashboard_only=True):
        version_error = check_version(self.request)
        if version_error:
            return version_error

        raw_token = self._extract_token()
        if not raw_token:
            return status.HTTP_401_UNAUTHORIZED, 'Authentication token is missing.', None

        try:
            token = AccessToken(raw_token)
        except TokenError:
            return status.HTTP_401_UNAUTHORIZED, 'Authentication token is invalid or expired.', None

        try:
            user = UserAccount.objects.get(pk=token['user_id'], is_active=True)
        except UserAccount.DoesNotExist:
            return status.HTTP_401_UNAUTHORIZED, 'User not found.', None

        if dashboard_only and user.role not in UserAccount.DASHBOARD_ROLES:
            return status.HTTP_403_FORBIDDEN, 'This account is not allowed to access the dashboard.', None

        self.request.user = user
        return status.HTTP_200_OK, 'Authenticated.', {'user': user}

    def _extract_token(self):
        auth_header = self.request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            return auth_header.removeprefix('Bearer ').strip()
        return getattr(self.request, 'access_token', None)
