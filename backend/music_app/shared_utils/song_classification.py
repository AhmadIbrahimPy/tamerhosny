"""Auto-classifies a song's genre/mood (Song.Genre/Song.Mood - see
music_app.models.Song) from its title and lyrics, via
backend.main_app.shared_utils.llm_providers. A song is only classified
if it's currently blank/UNSPECIFIED - a value someone set by hand in
the dashboard is never overwritten.

This directly feeds the content-based fallback in
backend.main_app.shared_utils.song_recommendations (shared genre/mood
is one of its similarity signals), which is otherwise blind for a song
with too little play data to compare collaboratively - most songs on a
young catalog, and every song right after it's added.

Triggered automatically (see music_app.signals) whenever a song is
created or its lyrics are added, and also runnable in bulk via the
`classify_songs` management command for the existing backlog.
"""
import logging

from backend.main_app.shared_utils.llm_providers import ask_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You classify Arabic (mostly Egyptian) songs by genre and mood for a music archive site. Given a song's title and (when available) its lyrics, pick exactly one genre and one mood from the fixed lists provided - never invent a value outside them. If the lyrics are missing or too short to judge confidently, use the title and your general knowledge of the song/artist if you recognize it; if you genuinely can't tell, pick the closest reasonable guess rather than refusing - every field is required.

Respond with STRICT JSON ONLY - no markdown code fences, no commentary before or after - matching exactly this shape:
{
  "genre": "one of the exact genre codes given below",
  "mood": "one of the exact mood codes given below"
}"""


def _build_prompt(song):
    from backend.music_app.models import Song

    genre_options = '\n'.join(
        f'- {value}: {label}' for value, label in Song.Genre.choices if value != Song.Genre.UNSPECIFIED
    )
    mood_options = '\n'.join(
        f'- {value}: {label}' for value, label in Song.Mood.choices if value != Song.Mood.UNSPECIFIED
    )
    lyrics_excerpt = (song.lyrics or '').strip()[:2000]

    lines = [
        f'Song title: {song.title_ar or song.title_en}',
    ]
    if song.title_en and song.title_en != song.title_ar:
        lines.append(f'Title (English/transliterated): {song.title_en}')
    if lyrics_excerpt:
        lines.append(f'Lyrics:\n{lyrics_excerpt}')
    else:
        lines.append('(No lyrics available - judge from the title alone.)')
    lines.append('')
    lines.append('Genre options:')
    lines.append(genre_options)
    lines.append('')
    lines.append('Mood options:')
    lines.append(mood_options)
    return '\n'.join(lines)


def classify_song(song):
    """Returns (genre, mood) - both valid Song.Genre/Song.Mood values -
    or None if every LLM provider failed/is unconfigured. Does not save;
    caller decides what to do with the result (see classify_and_save).
    """
    from backend.music_app.models import Song

    data = ask_json(_build_prompt(song), SYSTEM_PROMPT, required_keys=('genre', 'mood'))
    if not data:
        return None

    genre = data.get('genre')
    mood = data.get('mood')
    valid_genres = {value for value, _ in Song.Genre.choices}
    valid_moods = {value for value, _ in Song.Mood.choices}
    if genre not in valid_genres or mood not in valid_moods:
        logger.warning('[song_classification] invalid genre/mood for song %s: %r/%r', song.pk, genre, mood)
        return None
    return genre, mood


def classify_and_save(song, force=False):
    """Classifies `song` and saves genre/mood if it was actually blank/
    UNSPECIFIED - safe to call on any song at any time, a no-op if it
    already has both set. Returns True if it changed anything.

    `force=True` reclassifies (and overwrites) even a song that already
    has both set - only meant for a one-off bulk correction of bad data
    (see the `classify_songs --force` management command), never from
    the automatic new-song/new-lyrics signals, which must never clobber
    a value someone genuinely set by hand.
    """
    from backend.music_app.models import Song

    needs_genre = force or not song.genre or song.genre == Song.Genre.UNSPECIFIED
    needs_mood = force or not song.mood or song.mood == Song.Mood.UNSPECIFIED
    if not needs_genre and not needs_mood:
        return False

    result = classify_song(song)
    if not result:
        return False
    genre, mood = result

    fields = {}
    if needs_genre:
        song.genre = genre
        fields['genre'] = genre
    if needs_mood:
        song.mood = mood
        fields['mood'] = mood

    # .update() (skips save()/signals) rather than song.save() - this is
    # a metadata-only change with nothing to do with the audio/cover
    # files a full save's pre_save signals also compress/process, and
    # triggering that unrelated work here for every classified song
    # would be pure overhead at best.
    Song.objects.filter(pk=song.pk).update(**fields)
    return True
