import json
import re

from django.conf import settings

from config.custom_packages.encryption import ChaCha20Cipher

ADMIN_PATH_PREFIX = f'/{settings.ADMIN_URL_PATH}'

_EXEMPT_PREFIXES = (ADMIN_PATH_PREFIX, '/static/', '/media/')


def _is_exempt(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in _EXEMPT_PREFIXES)


class CustomMiddleware:
    """Decrypts the encrypted auth cookies and attaches plain values to
    the request, mirroring the mobile/dashboard client's cookie contract.
    """

    ENCRYPTED_COOKIES = ('access_token', 'session_token', 'device_token', 'user_meta')

    def __init__(self, get_response):
        self.get_response = get_response
        self.cipher = ChaCha20Cipher(settings.COOKIE_ENCRYPTION_KEY)

    def __call__(self, request):
        request.access_token = self._read(request, 'access_token')
        request.session_token = self._read(request, 'session_token')
        request.device_token = self._read(request, 'device_token')

        raw_meta = self._read(request, 'user_meta')
        try:
            request.user_meta_object = json.loads(raw_meta) if raw_meta else {}
        except (TypeError, ValueError):
            request.user_meta_object = {}

        request.lang_code = request.COOKIES.get('lang_code', 'ar')

        return self.get_response(request)

    def _read(self, request, cookie_name):
        raw = request.COOKIES.get(cookie_name)
        if not raw:
            return None
        return self.cipher.decrypt(raw)


class DisableCSRFMiddleware:
    """Skip CSRF enforcement once the caller has already proven identity
    via the encrypted access-token cookie.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if _is_exempt(request.path) or getattr(request, 'access_token', None):
            setattr(request, '_dont_enforce_csrf_checks', True)
        return self.get_response(request)


class DynamicCSRFMiddleware:
    """Skip CSRF enforcement when the Origin header matches one of the
    app's own trusted domains.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.trusted_origin_patterns = [
            re.compile(pattern) for pattern in settings.DYNAMIC_CSRF_TRUSTED_ORIGIN_REGEXES
        ]

    def __call__(self, request):
        if _is_exempt(request.path):
            setattr(request, '_dont_enforce_csrf_checks', True)
            return self.get_response(request)

        origin = request.META.get('HTTP_ORIGIN', '')
        if origin and any(pattern.match(origin) for pattern in self.trusted_origin_patterns):
            setattr(request, '_dont_enforce_csrf_checks', True)

        return self.get_response(request)
