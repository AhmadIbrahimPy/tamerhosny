from rest_framework import status

# Client-app version gate, independent of DRF's own API versioning.
# 'available'     -> version is live and accepted, mapped to the platforms it supports
# 'not_available' -> version is deprecated, caller must upgrade
# 'upcoming'      -> version is not released yet
versions = {
    'available': {
        '1.0.0': ['DASHBOARD', 'WEBSITE'],
    },
    'not_available': {},
    'upcoming': {},
}


def check_version(request):
    """Gate a request by client app version/platform, before any auth or
    business logic runs. Returns a (status, details, data) tuple, or None
    when the check passes.
    """
    ver = request.headers.get('ver')
    plat = request.headers.get('plat')

    if not ver or not plat:
        return status.HTTP_400_BAD_REQUEST, 'ver/plat headers are required', None

    if ver in versions['not_available']:
        return status.HTTP_410_GONE, 'This app version is no longer supported, please update.', None

    if ver in versions['upcoming']:
        return status.HTTP_425_TOO_EARLY, 'This app version has not been released yet.', None

    supported_platforms = versions['available'].get(ver)
    if not supported_platforms:
        return status.HTTP_404_NOT_FOUND, 'Unknown app version.', None

    if plat not in supported_platforms:
        return status.HTTP_406_NOT_ACCEPTABLE, 'This platform is not supported for this app version.', None

    return None
