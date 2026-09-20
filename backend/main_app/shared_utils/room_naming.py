"""AI-generated names for "اسمع معاه" listening rooms (see
ListenTogetherRoom in backend.main_app.models) - only used when the
host hasn't picked their own name. Song.genre/mood are already cached
on every song by backend.music_app.shared_utils.song_classification
(a separate, existing Celery pipeline) - this feeds those straight into
the prompt instead of re-deriving mood itself.

Called from generate_room_name_task (backend.main_app.tasks), never
inline in a request - see that task's own docstring for why.
"""

import logging

from backend.main_app.shared_utils.llm_providers import ask_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """أنت بتخترع اسم شقي وجذاب لـ"جروب سماع" على موقع مصري لأغاني تامر حسني - جروب بيتفرج فيه ناس على شخص واحد وهو بيسمع أغنية. الاسم ده بيتحط بدل اسم صاحب الجروب في قائمة عامة، فلازم يكون خفيف ومصري ومضحك شوية ويلمح للحالة/النوع اللي بيسمعه من غير ما يذكر اسم الأغنية أو المغني نفسه.

الأسلوب: لقب "خبير/معلم/حريف" في الحالة اللي بيسمعها - مثال: أغنية حزينة -> "حريف في الحزن"، أغنية شعبي/مهرجانات حماسية -> "معلم في الروشنة"، أغنية رومانسية -> "أسطورة الغرام"، أغنية فرح/احتفال -> "بطل الفرحة". اخترع، متلزمش بالأمثلة دي حرفياً.

رد بـ JSON فقط، من غير أي نص تاني، بالشكل ده بالظبط:
{"title": "..."}

الاسم لازم يكون من 2 لـ4 كلمات بالعربي، من غير علامات ترقيم زيادة."""

# Falls back to this if every LLM provider fails/is unconfigured - the
# room still needs SOME name the moment it's created (ListenTogetherRoom.
# display_name already falls back to "جروب {username}" when both
# custom_name and generated_name are blank, so this is a nicer-than-
# nothing upgrade over that, not a hard requirement).
FALLBACK_NAMES = [
    'جروب سماع مباشر',
    'جلسة سماع حصرية',
    'زاوية الاستماع',
]


def _build_prompt(song):
    lines = [f'بيسمع دلوقتي: {song.title_ar or song.title_en}']
    if song.genre:
        lines.append(f'النوع: {song.get_genre_display()}')
    if song.mood:
        lines.append(f'الحالة/المود: {song.get_mood_display()}')
    return '\n'.join(lines)


def generate_room_name(song):
    """Returns a short Arabic room title string - always something,
    never None (falls back to a generic name on LLM failure).
    """
    import random

    if song is None:
        return random.choice(FALLBACK_NAMES)

    data = ask_json(_build_prompt(song), SYSTEM_PROMPT, required_keys=('title',))
    title = (data or {}).get('title', '').strip()

    if not title or len(title) > 60:
        logger.warning('[room_naming] unusable title for song %s: %r', song.pk, title)
        return random.choice(FALLBACK_NAMES)

    return title
