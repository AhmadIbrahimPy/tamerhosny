from django import template
from django.utils.translation import get_language

register = template.Library()

# Bootstrap Icons already ships reliable brand glyphs for the common
# social platforms - used as the fallback for an ExternalLink whose
# Platform has no logo_icon_url set (a freshly-added platform, or one
# where the admin hasn't bothered hunting down a hotlinked logo image),
# instead of always falling back to the same generic external-link
# icon regardless of which platform it actually is.
_PLATFORM_ICON_CLASSES = {
    'FACEBOOK': 'bi-facebook',
    'INSTAGRAM': 'bi-instagram',
    'TIKTOK': 'bi-tiktok',
    'TWITTER': 'bi-twitter-x',
    'SNAPCHAT': 'bi-snapchat',
    'LINKEDIN': 'bi-linkedin',
    'THREADS': 'bi-threads',
    'YOUTUBE': 'bi-youtube',
    'SPOTIFY': 'bi-spotify',
    'WEBSITE': 'bi-globe2',
    'EMAIL': 'bi-envelope-fill',
}


@register.filter(name='platform_icon_class')
def platform_icon_class(platform_name):
    """See _PLATFORM_ICON_CLASSES above - 'bi-box-arrow-up-right' (a
    plain external-link glyph) for anything not in that map.
    """
    return _PLATFORM_ICON_CLASSES.get(platform_name, 'bi-box-arrow-up-right')


@register.filter(name='localized_field')
def localized_field(obj, field_prefix):
    """The Arabic/English pair (e.g. title_ar/title_en, full_name_ar/
    full_name_en) picked for the site's current language — falling back
    to whichever one is actually filled in when the preferred one is
    blank (most content only has the Arabic name entered).
    """
    if obj is None:
        return ''
    ar_value = getattr(obj, f'{field_prefix}_ar', '') or ''
    en_value = getattr(obj, f'{field_prefix}_en', '') or ''
    if get_language() == 'en':
        return en_value or ar_value
    return ar_value or en_value


@register.filter(name='first_word')
def first_word(value):
    words = (value or '').split()
    return words[0] if words else ''


@register.filter(name='floordiv')
def floordiv(value, arg):
    return int(value) // int(arg)


@register.filter(name='modulo')
def modulo(value, arg):
    return int(value) % int(arg)
