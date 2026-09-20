""""اسمع معاه" - look up what a specific user is listening to right now.

CurrentSongListener (see backend.main_app.consumers.SongListenerConsumer)
is normally queried by song - "who's listening to this song" - never by
user. This is the reverse lookup: given a user, what are they listening
to, if anything, used to decide whether a "Listen with them" button
shows on their public profile.
"""

from datetime import timedelta

from django.utils import timezone

from backend.main_app.models import CurrentSongListener

# Same cutoff SongListenerConsumer uses to treat a listener as gone
# without waiting for a clean disconnect (a hard process kill skips it).
STALE_LISTENER_CUTOFF = timedelta(minutes=5)


def get_current_song_for_user(user):
    """The Song `user` is actively listening to right now, or None.

    A user is only ever meant to hold one live CurrentSongListener row
    at a time (one tab actually playing), but nothing enforces that -
    picks the most recently started if there happens to be more than
    one.
    """

    if user is None or not user.is_authenticated:
        return None

    cutoff = timezone.now() - STALE_LISTENER_CUTOFF

    listener = (
        CurrentSongListener.objects
        .filter(user=user, last_heartbeat__gte=cutoff)
        .select_related('song')
        .first()
    )

    return listener.song if listener else None
