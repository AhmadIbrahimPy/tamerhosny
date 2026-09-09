"""Best-effort Arabic/Egyptian profanity detection for admin-facing
transcript displays (see dashboard_app.views.user_view's voice tab) -
not a moderation/enforcement tool and not applied anywhere public; just
softens the default display of a spoken voice-assistant transcript
that happens to contain a curse word, with a click-to-reveal toggle in
the template for an admin who actually needs to read the real text.

The word list is deliberately short and representative rather than
exhaustive - a simple substring match, so it will miss creative
spellings/spacing and can occasionally false-positive on an innocent
word that happens to contain one as a substring. Fine for its actual
job (soften a display, not gate access to anything).
"""
import re

_PROFANITY_WORDS = [
    'كس', 'طيز', 'زبي', 'خول', 'متناك', 'شرموط', 'عرص', 'قحبة', 'قحبه',
    'ابن كلب', 'يلعن', 'كسمك', 'وسخة', 'وسخه', 'نيك', 'كلب ابن كلب',
]

_PROFANITY_RE = re.compile('|'.join(re.escape(w) for w in _PROFANITY_WORDS))


def mask_profanity(text):
    """Returns (display_text, was_flagged) - display_text has every
    matched word replaced with asterisks of the same length; the rest
    of the sentence is untouched either way.
    """
    if not text:
        return text, False

    flagged = False

    def _replace(match):
        nonlocal flagged
        flagged = True
        return '*' * len(match.group(0))

    masked = _PROFANITY_RE.sub(_replace, text)
    return masked, flagged
