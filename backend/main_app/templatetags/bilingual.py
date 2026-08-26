from django import template
from django.utils.translation import get_language

register = template.Library()


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


@register.filter(name='floordiv')
def floordiv(value, arg):
    return int(value) // int(arg)


@register.filter(name='modulo')
def modulo(value, arg):
    return int(value) % int(arg)
