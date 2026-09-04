"""Public website authentication - entirely separate from the internal
dashboard login (backend/dashboard_app/views.py, a different URL, a
different template, restricted to staff roles). Everything here signs
in a regular visitor (UserAccount.Role.VIEWER) via the normal Django
session, for a JS modal rather than a full page: every view returns
JSON and expects the request as either JSON or a normal POST body.

Covers: email/password register and login, "Sign in with Google"
(manual OAuth2 - GOOGLE_OAUTH_CLIENT_ID/SECRET in credentials/.env),
and a three-step forgot-password flow (request a code by email, verify
it, set a new password).
"""
import json
import re
import urllib.parse
import urllib.request

from django.conf import settings
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from backend.main_app.models import PasswordResetCode, UserAccount

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def _safe_next_path(request, candidate):
    """A relative in-site path to bounce back to, or '/' if candidate is
    missing/unsafe (open-redirect check - Google echoes 'state' back
    verbatim, so it must be re-validated, not just trusted)."""
    if candidate and url_has_allowed_host_and_scheme(
        candidate, allowed_hosts={request.get_host()}, require_https=request.is_secure(),
    ):
        return candidate
    return '/'


def _json_body(request):
    if request.content_type == 'application/json':
        try:
            return json.loads(request.body or b'{}')
        except ValueError:
            return {}
    return request.POST


def _error(message, status=400):
    return JsonResponse({'status': 'error', 'message': str(message)}, status=status)


def _user_payload(user):
    return {
        'username': user.username,
        'name': user.first_name or user.username,
        'email': user.email,
        'profile_image': user.profile_image.url if user.profile_image else None,
    }


def _unique_username(base):
    base = re.sub(r'[^a-zA-Z0-9_.]', '', base.split('@')[0]).lower() or 'user'
    username = base
    suffix = 0
    while UserAccount.objects.filter(username=username).exists():
        suffix += 1
        username = f'{base}{suffix}'
    return username


@csrf_exempt
@require_POST
def register(request):
    if request.user.is_authenticated:
        return _error(_('أنت مسجل الدخول بالفعل.'))

    data = _json_body(request)
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not name:
        return _error(_('من فضلك أدخل الاسم.'))
    if not EMAIL_RE.match(email):
        return _error(_('بريد إلكتروني غير صالح.'))
    if len(password) < 8:
        return _error(_('كلمة السر لازم تكون 8 حروف على الأقل.'))
    if UserAccount.objects.filter(email__iexact=email).exists():
        return _error(_('البريد الإلكتروني ده مسجل بالفعل.'))

    user = UserAccount(
        username=_unique_username(email),
        email=email,
        first_name=name,
        role=UserAccount.Role.VIEWER,
    )
    user.set_password(password)
    profile_image = request.FILES.get('profile_image')
    if profile_image:
        user.profile_image = profile_image
    user.save()

    auth_login(request, user)
    return JsonResponse({'status': 'success', 'user': _user_payload(user)})


@csrf_exempt
@require_POST
def login_view(request):
    if request.user.is_authenticated:
        return _error(_('أنت مسجل الدخول بالفعل.'))

    data = _json_body(request)
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    user = UserAccount.objects.filter(email__iexact=email).first()
    if not user:
        return _error(_('البريد الإلكتروني أو كلمة السر غير صحيحة.'))
    if not user.has_usable_password():
        return _error(_('الحساب ده اتعمل بجوجل - سجل دخولك بجوجل بدل كده.'))

    authenticated = authenticate(request, username=user.username, password=password)
    if not authenticated:
        return _error(_('البريد الإلكتروني أو كلمة السر غير صحيحة.'))

    auth_login(request, authenticated)
    return JsonResponse({'status': 'success', 'user': _user_payload(authenticated)})


@csrf_exempt
@require_POST
def logout_view(request):
    user = request.user if request.user.is_authenticated else None
    auth_logout(request)

    if user is not None:
        # The client-side WS 'stop' signal (sent when logout pauses
        # playback) races the connection teardown on the redirect that
        # follows - if it lost that race, this user's "currently
        # listening" row would outlive their session, showing up as
        # someone still logged in and listening on a song they're no
        # longer even authenticated for. Clean it up here unconditionally
        # instead of relying on that timing.
        from backend.main_app.models import CurrentSongListener
        from backend.main_app.shared_utils.song_leaderboard import broadcast_current_leaderboard

        song_ids = list(
            CurrentSongListener.objects.filter(user=user).values_list('song_id', flat=True).distinct()
        )
        CurrentSongListener.objects.filter(user=user).delete()

        if song_ids:
            from asgiref.sync import async_to_sync
            from channels.layers import get_channel_layer

            channel_layer = get_channel_layer()
            for song_id in song_ids:
                broadcast_current_leaderboard(song_id)
                if channel_layer is not None:
                    count = CurrentSongListener.objects.filter(song_id=song_id).count()
                    async_to_sync(channel_layer.group_send)(f'song_{song_id}_listeners', {
                        'type': 'listener.count',
                        'count': count,
                    })

    return JsonResponse({'status': 'success'})


@csrf_exempt
@require_POST
def forgot_password_request(request):
    data = _json_body(request)
    email = (data.get('email') or '').strip().lower()

    user = UserAccount.objects.filter(email__iexact=email).first()
    # Same response either way - don't reveal whether an email is
    # registered. The code just silently never arrives if it isn't (or
    # if the account is Google-only, which has no password to reset).
    if user and user.has_usable_password():
        reset_code = PasswordResetCode.generate(user)
        send_mail(
            subject=str(_('كود استعادة كلمة السر')),
            message=str(_('كود استعادة كلمة السر بتاعك هو: %(code)s\nصالح لمدة 15 دقيقة.')) % {'code': reset_code.code},
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
    return JsonResponse({'status': 'success'})


@csrf_exempt
@require_POST
def forgot_password_verify(request):
    data = _json_body(request)
    email = (data.get('email') or '').strip().lower()
    code = (data.get('code') or '').strip()

    user = UserAccount.objects.filter(email__iexact=email).first()
    if not user:
        return _error(_('الكود غير صحيح أو منتهي.'))

    reset_code = user.password_reset_codes.filter(code=code, used_at__isnull=True).first()
    if not reset_code or not reset_code.is_valid:
        return _error(_('الكود غير صحيح أو منتهي.'))

    return JsonResponse({'status': 'success'})


@csrf_exempt
@require_POST
def forgot_password_reset(request):
    data = _json_body(request)
    email = (data.get('email') or '').strip().lower()
    code = (data.get('code') or '').strip()
    new_password = data.get('password') or ''

    if len(new_password) < 8:
        return _error(_('كلمة السر لازم تكون 8 حروف على الأقل.'))

    user = UserAccount.objects.filter(email__iexact=email).first()
    if not user:
        return _error(_('الكود غير صحيح أو منتهي.'))

    reset_code = user.password_reset_codes.filter(code=code, used_at__isnull=True).first()
    if not reset_code or not reset_code.is_valid:
        return _error(_('الكود غير صحيح أو منتهي.'))

    user.set_password(new_password)
    user.save(update_fields=['password'])
    reset_code.used_at = timezone.now()
    reset_code.save(update_fields=['used_at'])

    auth_login(request, user)
    return JsonResponse({'status': 'success', 'user': _user_payload(user)})


# ---------------------------------------------------------------------------
# Google OAuth (manual flow - no extra dependency). GOOGLE_OAUTH_CLIENT_ID
# empty means it's not configured yet: the button stays visible (per the
# product ask) but sends the visitor to a clear error instead of a
# broken Google screen.
# ---------------------------------------------------------------------------

GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v3/userinfo'


def google_login_start(request):
    if not settings.GOOGLE_OAUTH_CLIENT_ID:
        return redirect('/?google_auth_error=not_configured')

    params = {
        'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
        'redirect_uri': settings.GOOGLE_OAUTH_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'openid email profile',
        'prompt': 'select_account',
        # Google echoes 'state' back verbatim to the callback - carrying
        # the page the visitor started from here is what lets the
        # callback return them to it (a song page, mid-playback-gate)
        # instead of always landing on the homepage.
        'state': _safe_next_path(request, request.GET.get('next')),
    }
    return redirect(f'{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}')


def google_login_callback(request):
    # The exact page the visitor started from (set by google_login_start,
    # already re-validated there) - every redirect below returns them to
    # it instead of always landing on the homepage.
    next_path = _safe_next_path(request, request.GET.get('state'))
    error_redirect = redirect(
        next_path + ('&' if '?' in next_path else '?') + 'google_auth_error=1',
    )

    code = request.GET.get('code')
    if not code or not settings.GOOGLE_OAUTH_CLIENT_ID:
        return error_redirect

    try:
        token_data = urllib.parse.urlencode({
            'code': code,
            'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
            'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET,
            'redirect_uri': settings.GOOGLE_OAUTH_REDIRECT_URI,
            'grant_type': 'authorization_code',
        }).encode()
        token_request = urllib.request.Request(GOOGLE_TOKEN_URL, data=token_data, method='POST')
        with urllib.request.urlopen(token_request, timeout=10) as response:
            tokens = json.loads(response.read())

        userinfo_request = urllib.request.Request(
            GOOGLE_USERINFO_URL, headers={'Authorization': f'Bearer {tokens["access_token"]}'},
        )
        with urllib.request.urlopen(userinfo_request, timeout=10) as response:
            profile = json.loads(response.read())
    except Exception:
        return error_redirect

    email = (profile.get('email') or '').strip().lower()
    if not email:
        return error_redirect

    user = UserAccount.objects.filter(email__iexact=email).first()
    if not user:
        user = UserAccount(
            username=_unique_username(email),
            email=email,
            first_name=profile.get('name') or email.split('@')[0],
            role=UserAccount.Role.VIEWER,
        )
        # No usable password - has_usable_password() then reports False,
        # which is exactly what marks this as a Google-only account
        # elsewhere (blocking password login/reset for it).
        user.set_unusable_password()
        user.save()

    auth_login(request, user)
    return redirect(next_path)
