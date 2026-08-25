from django.utils.crypto import get_random_string
from django.utils.text import slugify

_RANDOM_CHARS = 'abcdefghijklmnopqrstuvwxyz0123456789'


def generate_ascii_slug(model_cls, title_en, fallback_prefix):
    """Build a URL-safe (Latin-only) slug: from the English title when one
    is set, otherwise a short random one. Arabic titles are never used for
    slugs — an all-Arabic slug gets percent-encoded into an unreadable mess
    in the address bar, so we don't fall back to allow_unicode Arabic here.
    """
    base = slugify(title_en) if title_en else ''
    if not base:
        base = f'{fallback_prefix}-{get_random_string(8, allowed_chars=_RANDOM_CHARS)}'
    slug = base
    suffix = 2
    while model_cls.objects.filter(slug=slug).exists():
        slug = f'{base}-{suffix}'
        suffix += 1
    return slug
