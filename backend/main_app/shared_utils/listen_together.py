""""اسمع معاه" - look up what a specific user is listening to right now.

CurrentSongListener (see backend.main_app.consumers.SongListenerConsumer)
is normally queried by song - "who's listening to this song" - never by
user. This is the reverse lookup: given a user, what are they listening
to, if anything, used to decide whether a "Listen with them" button
shows on their public profile.
"""

from datetime import timedelta

from django.db import models
from django.urls import reverse
from django.utils import timezone

from backend.main_app.models import CurrentSongListener

# Same cutoff SongListenerConsumer uses to treat a listener as gone
# without waiting for a clean disconnect (a hard process kill skips it).
STALE_LISTENER_CUTOFF = timedelta(minutes=5)

# Shared between seed_fake_live_rooms (the management command that
# creates these) and keep_seed_rooms_alive (backend.main_app.tasks, the
# celery-beat task that keeps them from aging out of the exact same
# staleness sweeps above) - every fake account either of them touches is
# tagged with this email domain, nothing else. Living here (not defined
# in the command module itself) so the task doesn't need to import from
# backend.main_app.management.commands.*, and so
# `UserAccount.objects.filter(email__iendswith='@' + SEED_EMAIL_DOMAIN).delete()`
# is the one line that ever needs to find every seeded account to wipe
# them back out again.
SEED_EMAIL_DOMAIN = 'thseed.local'


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


def record_song_play(user, song):
    """Credits `user` with one listen of `song` - the exact same
    once-per-user-per-song-per-hour dedup website_app.views.increment_play_count
    uses for its own POST /songs/increment-play/ endpoint, extracted here
    so ListenTogetherConsumer can credit a whole room's worth of people
    (the host who started the song, plus everyone else in
    ListenTogetherViewer) the same way a solo listener earns a play,
    instead of only ever crediting whoever's browser happens to send the
    HTTP ping.

    Returns True if this call actually incremented the count, False if
    the dedup window suppressed it (mirrors 'incremented' in that view's
    JSON response) - callers that don't care can ignore the return value.
    """
    from backend.main_app.models import UserSongPlay

    if song.is_duet or user is None or not user.is_authenticated:
        return False

    user_play, created = UserSongPlay.objects.get_or_create(user=user, song=song)

    if not created and user_play.last_played_at:
        if timezone.now() - user_play.last_played_at < timedelta(hours=1):
            return False

    song.__class__.objects.filter(pk=song.pk).update(play_count=models.F('play_count') + 1)

    user_play.play_count += 1
    user_play.last_played_at = timezone.now()
    user_play.save()

    return True


def serialize_song_for_listen_together(song):
    """The song payload playAudio() (base.html) expects - shared by
    public_profile's single button, live_rooms' one-per-slide feed, and
    the live_rooms_feed push (SongListenerConsumer._maybe_open_room), so
    all three stay in the exact same shape."""
    from backend.main_app.templatetags.bilingual import localized_field
    from backend.music_app.models import SongCredit

    singers = [
        credit for credit in song.credits.select_related('person').all()
        if credit.role in (SongCredit.Role.SINGER, SongCredit.Role.FEATURED_ARTIST)
    ]
    return {
        'songId': song.pk,
        'title': localized_field(song, 'title'),
        'artist': ', '.join(localized_field(credit.person, 'full_name') for credit in singers),
        'album': localized_field(song.album, 'title') if song.album else '',
        'albumLink': reverse('website_app:album-detail', args=[song.album.slug]) if song.album else '',
        'image': song.display_cover_url or '',
        'url': song.audio_file.url if song.audio_file else '',
        'link': reverse('website_app:song-detail', args=[song.slug]),
    }
