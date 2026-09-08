"""Tracks which Song.Mood a user has actually been leaning into recently
(see main_app.models.UserMoodScore), so "recommended for you"
(main_app.shared_utils.song_recommendations) can lean the same way.

Same exponential-decay approach as the leaderboard/play-history scores
(main_app.shared_utils.song_leaderboard), but on a much shorter half-life
- a mood is meant to read as "the last couple of days", not "this
user's whole listening history". record_mood_signal() is called from
record_full_listen() (song_leaderboard.py) - the same "a full, natural
listen" signal already used everywhere else, not raw play counts.
"""
import math

from django.utils import timezone

HALF_LIFE_DAYS = 3.0
DECAY_LAMBDA = math.log(2) / HALF_LIFE_DAYS


def record_mood_signal(user, song):
    """Bumps the user's score for `song.mood`, decaying it (and every
    other mood of theirs) up to now first - same math as
    song_leaderboard.record_full_listen, just per-mood instead of
    per-song. A no-op for a song with no mood set yet.
    """
    from backend.main_app.models import UserMoodScore

    if not song.mood or song.mood == song.Mood.UNSPECIFIED:
        return

    now = timezone.now()
    entry, _created = UserMoodScore.objects.get_or_create(user=user, mood=song.mood)

    if entry.score_updated_at:
        elapsed_days = (now - entry.score_updated_at).total_seconds() / 86400
        decayed = entry.decayed_score * math.exp(-DECAY_LAMBDA * max(elapsed_days, 0))
    else:
        decayed = 0.0

    entry.decayed_score = decayed + 1.0
    entry.score_updated_at = now
    entry.save(update_fields=['decayed_score', 'score_updated_at'])


def current_mood_scores(user):
    """{mood: current_decayed_score} for every mood this user has ever
    registered a signal for, decayed up to now (not just as of whenever
    it was last written) - the read-time recompute the leaderboard's
    own get_cached_leaderboard uses the same trick for.
    """
    from backend.main_app.models import UserMoodScore

    now = timezone.now()
    scores = {}
    for entry in UserMoodScore.objects.filter(user=user):
        if entry.score_updated_at:
            elapsed_days = (now - entry.score_updated_at).total_seconds() / 86400
            scores[entry.mood] = entry.decayed_score * math.exp(-DECAY_LAMBDA * max(elapsed_days, 0))
        else:
            scores[entry.mood] = entry.decayed_score
    return scores


def current_mood(user, minimum_score=0.5):
    """The single mood this user is leaning into most right now, or None
    if nothing's strong enough yet (a brand new listener, or everything's
    decayed away) - `minimum_score` avoids calling a barely-there signal
    (e.g. 0.05 left over from one listen a week ago) an actual "mood".
    """
    scores = current_mood_scores(user)
    if not scores:
        return None
    mood, score = max(scores.items(), key=lambda pair: pair[1])
    return mood if score >= minimum_score else None
