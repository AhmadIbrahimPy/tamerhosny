"""Background analysis of a voice command the fixed regex patterns (and
the live AI fallback) failed to resolve - reuses the same LLM chain
(llm_providers.ask_json) already used for live classification, but also
asks it for a handful of paraphrases of the same request in different
wording. The result is stored as a VoiceKnownPhrase row that
website_app.views.voice_intent() checks (fuzzy match against the
original transcript and every paraphrase) before ever calling the LLM
again - a request phrased similarly to one seen before then resolves
from this local table instantly.

Triggered from website_app.views.voice_log on a COMMAND_FAILED event
(see backend.main_app.tasks.analyze_failed_voice_command) - always
fire-and-forget, since a missed learning opportunity is never worth
surfacing as an error to anyone.
"""
from backend.main_app.shared_utils.llm_providers import ask_json
from backend.main_app.shared_utils.voice_shared import VOICE_NAV_PAGES, VOICE_VALID_INTENTS

_SYSTEM_PROMPT = """You are analyzing a voice command that an Arabic Tamer Hosny fan website's voice assistant failed to understand the first time, so the site can learn to recognize similarly-worded requests in the future.

Respond with STRICT JSON ONLY (no markdown fences, no commentary) matching exactly this shape:
{
  "intent": one of "next", "previous", "stop", "resume", "seek_forward", "seek_backward", "like", "unlike", "open_current_song", "play_song", "play_mood", "play_random", "navigate", "unknown",
  "song_query": the song title/name mentioned (for play_song), or null,
  "mood": one of "ROMANTIC", "SAD_HEARTBREAK", "ENERGETIC_UPBEAT", "MOTIVATIONAL_HOPEFUL", "CHILL_RELAXING", "NOSTALGIC", "CONFIDENT_PLAYFUL" (for play_mood), or null,
  "page": one of __PAGES__ (for navigate), or null,
  "paraphrases": a list of 4 to 6 short alternative Egyptian Arabic phrasings that express the exact same request in different wording - natural things a real person might say instead, not translations or synonyms of individual words
}

Guidance:
- next/previous are for switching to a whole different track.
- seek_forward/seek_backward move a few seconds within the SAME song currently playing - never confuse these with next/previous.
- stop/resume are pause/play of the current song.
- like/unlike is about liking or unliking whatever song is currently playing.
- open_current_song means "open the page for whatever song is playing right now" - never pick this for a request naming a specific different song/album/person.
- play_song is for "play <specific song name>" - extract just the title into song_query.
- play_mood is for a request to play something matching a mood/feeling, not a specific title.
- play_random is for a request to just play *something* with no specific song or mood given at all.
- navigate is ONLY for going to one of the fixed site sections listed above.
- Use "unknown" whenever the command doesn't clearly and confidently fit one of the above - for "unknown", paraphrases can be an empty list.

Every key must be present; use null for any that don't apply to the chosen intent."""


def analyze_and_store(transcript):
    """Classifies `transcript` and stores it (with AI-generated
    paraphrases) as a VoiceKnownPhrase. Returns the created row, or
    None if nothing useful was learned (empty input, every provider
    failed, or the AI itself couldn't confidently classify it either).
    """
    from backend.main_app.models import VoiceKnownPhrase
    from backend.music_app.models import Song

    transcript = (transcript or '').strip()[:300]
    if not transcript:
        return None

    system_prompt = _SYSTEM_PROMPT.replace('__PAGES__', str(list(VOICE_NAV_PAGES.keys())))
    data = ask_json(transcript, system_prompt, required_keys=('intent',))
    if not data:
        return None

    intent = data.get('intent') if data.get('intent') in VOICE_VALID_INTENTS else 'unknown'
    if intent == 'unknown':
        return None  # nothing useful learned - don't pollute the table with dead ends

    mood = data.get('mood')
    mood = mood if mood in Song.Mood.values else ''

    page = data.get('page')
    page = page if page in VOICE_NAV_PAGES else ''

    song_query = data.get('song_query')
    song_query = song_query.strip()[:200] if isinstance(song_query, str) and song_query.strip() else ''

    if intent == 'navigate' and not page:
        return None
    if intent == 'play_mood' and not mood:
        return None
    if intent == 'play_song' and not song_query:
        return None

    paraphrases = data.get('paraphrases')
    if not isinstance(paraphrases, list):
        paraphrases = []
    paraphrases = [p.strip()[:300] for p in paraphrases if isinstance(p, str) and p.strip()][:8]

    return VoiceKnownPhrase.objects.create(
        original_transcript=transcript,
        intent=intent,
        song_query=song_query,
        mood=mood,
        page=page,
        paraphrases=paraphrases,
    )
