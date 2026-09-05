from geoip2fast import GeoIP2Fast
from user_agents import parse as parse_user_agent

from backend.main_app.models import LoginSession, UserAccount

_geoip = GeoIP2Fast()


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _describe_device(ua_string):
    ua = parse_user_agent(ua_string)
    bits = [
        ua.device.family if ua.device.family and ua.device.family != 'Other' else None,
        f'{ua.os.family} {ua.os.version_string}'.strip() if ua.os.family else None,
        f'{ua.browser.family} {ua.browser.version_string}'.strip() if ua.browser.family else None,
    ]
    return ' - '.join(bit for bit in bits if bit)


def _approximate_location(ip_address):
    if not ip_address:
        return '', ''
    try:
        result = _geoip.lookup(ip_address)
    except Exception:
        return '', ''
    if not result or result.is_private:
        return '', ''
    return result.country_code, result.country_name


def record_login_session(request, user, source):
    """Log one successful login (dashboard or app/site) with its device,
    approximate IP-based location (resolved offline, no external service
    calls), and whether the account is a dashboard admin/editor.
    """
    ip_address = _client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    country_code, country_name = _approximate_location(ip_address)

    LoginSession.objects.create(
        user=user,
        source=source,
        is_admin=user.role in UserAccount.DASHBOARD_ROLES,
        ip_address=ip_address,
        user_agent=user_agent[:500],
        device=_describe_device(user_agent)[:150],
        country_code=country_code,
        country_name=country_name,
    )
