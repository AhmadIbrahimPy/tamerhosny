"""Shared constants for the voice assistant's AI intent classification -
used by both the live endpoint (backend.website_app.views.voice_intent)
and the background learning task (backend.main_app.tasks.
analyze_failed_voice_command / backend.main_app.shared_utils.
voice_command_learning) that reuses the exact same validation. Kept
here (main_app, not website_app) so the background task can import it
without website_app ever having to import from main_app.tasks at
module load time - main_app already sits below website_app in the
dependency direction everywhere else in this codebase.
"""

# Fixed, safe set of site sections the voice assistant's "navigate" intent
# is allowed to land on - deliberately only whole-catalog list/home pages,
# never a specific song/album/person's own page (there's no reliable way
# for the LLM to resolve "افتح صفحة الأغنية اللي شغالة" to a slug - that's
# handled entirely client-side instead, from whatever's actually playing).
VOICE_NAV_PAGES = {
    'home': '/',
    'bio': '/tamer-hosny/',
    'player': '/player/',
    'songs': '/songs/',
    'albums': '/albums/',
    'people': '/people/',
    'movies': '/movies/',
    'series': '/series/',
    'commercials': '/commercials/',
    'concerts': '/concerts/',
    'daily_guess': '/guess/',
    'leaderboard': '/leaderboard/',
    'likes': '/likes/',
    'duets': '/my-duets/',
    'recently_played': '/recently-played/',
    'playlists': '/playlists/',
    'remixes': '/remixes/',
}

VOICE_VALID_INTENTS = {
    'next', 'previous', 'stop', 'resume', 'seek_forward', 'seek_backward',
    'like', 'unlike', 'open_current_song', 'play_song', 'play_mood',
    'play_lyrics', 'play_random', 'navigate', 'unknown',
}
