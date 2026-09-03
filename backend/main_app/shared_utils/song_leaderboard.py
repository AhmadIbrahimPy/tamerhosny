"""The "who's listening now" leaderboard shown on a song's detail page.

Only people currently listening are shown at all - the moment someone
stops (pause, leave the page, the song ends/auto-advances, they log
out...), they drop out of the list; the moment they start, they appear.
That's driven entirely by CurrentSongListener presence (see
`_filter_to_live`), same signal as the plain listener count.

Within that live set, ranking rewards genuine engagement, not just
clicking play once:
- Only a FULL, natural listen (reached the end, not skipped or paused
  early) adds to a listener's score - see `record_full_listen`, called
  from the player's native 'ended' event.
- That score decays over time (exponential half-life) so someone who
  binged the song months ago doesn't keep outranking someone listening
  to it heavily this week.
- Liking the song multiplies the score, on top of listens.

The full (unfiltered) ranking is still persisted (SongLeaderboardRank)
so up/down/same/new trend arrows and the live-set ranks stay meaningful
across recomputes; only the *displayed* board is filtered down to who's
live right now. Broadcast over `song_{id}_leaderboard` on every score
change or presence change (start/stop listening).
"""
import math

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

TOP_N = 100
HALF_LIFE_DAYS = 7.0
DECAY_LAMBDA = math.log(2) / HALF_LIFE_DAYS
LIKE_MULTIPLIER = 1.25


def _group_name(song_id):
    return f'song_{song_id}_leaderboard'


def record_full_listen(user, song_id):
    """Call when a song finishes playing naturally for a logged-in user
    (not on skip/pause) - the one signal that should move the ranking.
    """
    from backend.main_app.models import UserSongPlay

    if user is None or not user.is_authenticated:
        return

    play, _ = UserSongPlay.objects.get_or_create(user=user, song_id=song_id)
    now = timezone.now()

    if play.score_updated_at:
        elapsed_days = (now - play.score_updated_at).total_seconds() / 86400
        decayed = play.decayed_score * math.exp(-DECAY_LAMBDA * elapsed_days)
    else:
        decayed = 0.0

    play.decayed_score = decayed + 1.0
    play.full_listen_count += 1
    play.score_updated_at = now
    play.save(update_fields=['decayed_score', 'full_listen_count', 'score_updated_at'])

    refresh_song_leaderboard(song_id)


def _serialize_user(user, rank, trend, full_listen_count, is_liked, is_live):
    return {
        'rank': rank,
        'trend': trend,
        'full_listen_count': full_listen_count,
        'is_liked': is_liked,
        'is_live': is_live,
        'username': user.username,
        'display_name': user.get_full_name() or user.username,
        'avatar_url': user.profile_image.url if user.profile_image else None,
    }


def _current_live_user_ids(song_id):
    from backend.main_app.models import CurrentSongListener

    return set(
        CurrentSongListener.objects.filter(song_id=song_id, user__isnull=False)
        .values_list('user_id', flat=True)
    )


def _live_only_entries(song_id, live_user_ids, already_ranked_user_ids):
    """Anyone currently listening who hasn't earned a ranked spot yet
    (no full listen, or too new for the decay to have caught up) still
    shouldn't just vanish from the list - show them unranked rather than
    leaving the board empty while people are visibly listening right now.
    """
    extra_ids = live_user_ids - already_ranked_user_ids
    if not extra_ids:
        return []

    from django.contrib.auth import get_user_model
    User = get_user_model()
    users = User.objects.filter(pk__in=extra_ids)
    return [
        _serialize_user(user, None, None, 0, False, True)
        for user in users
    ]


def _filter_to_live(entries):
    """Drop anyone not currently listening, then renumber the ones that
    are (by their real engagement rank) 1..N so the displayed list has
    no gaps. Live-but-unranked entries (rank=None) are already `is_live`
    by construction and keep their headphones-icon-instead-of-a-number
    treatment.
    """
    ranked_live = [e for e in entries if e['is_live'] and e['rank'] is not None]
    for index, entry in enumerate(ranked_live):
        entry['rank'] = index + 1
    unranked_live = [e for e in entries if e['is_live'] and e['rank'] is None]
    return ranked_live + unranked_live


def get_cached_leaderboard(song_id):
    """Cheap read of the last-computed board, filtered to who's live
    right now (see `_filter_to_live`) with presence refreshed fresh each
    time - too volatile to persist. Used when a viewer opens the modal
    and nothing score-changing has happened since.
    """
    from backend.main_app.models import SongLeaderboardRank

    rows = list(
        SongLeaderboardRank.objects.filter(song_id=song_id)
        .select_related('user').order_by('rank')
    )
    live_user_ids = _current_live_user_ids(song_id)
    entries = [
        _serialize_user(row.user, row.rank, row.trend, row.full_listen_count, row.is_liked, row.user_id in live_user_ids)
        for row in rows
    ]
    entries += _live_only_entries(song_id, live_user_ids, {row.user_id for row in rows})
    return _filter_to_live(entries)


def broadcast_current_leaderboard(song_id):
    """Re-sends the existing (unchanged) ranking with fresh `is_live`
    flags - call this when presence changes (someone starts/stops
    listening) so the live dot updates without needing a score recompute.
    """
    entries = get_cached_leaderboard(song_id)
    channel_layer = get_channel_layer()
    if channel_layer is not None:
        async_to_sync(channel_layer.group_send)(_group_name(song_id), {
            'type': 'leaderboard.update',
            'entries': entries,
        })


def refresh_song_leaderboard(song_id, broadcast=True):
    """Recomputes the top-N ranking (applying decay up to now and the
    like multiplier), persists it, and pushes it to every open
    leaderboard socket for this song.
    """
    from backend.main_app.models import Like, SongLeaderboardRank, UserSongPlay
    from backend.music_app.models import Song

    now = timezone.now()
    song_ct = ContentType.objects.get_for_model(Song)
    liked_user_ids = set(
        Like.objects.filter(content_type=song_ct, object_id=song_id).values_list('user_id', flat=True)
    )

    plays = list(
        UserSongPlay.objects.filter(song_id=song_id, full_listen_count__gt=0).select_related('user')
    )
    for play in plays:
        elapsed_days = (now - play.score_updated_at).total_seconds() / 86400 if play.score_updated_at else 0
        current_decay = play.decayed_score * math.exp(-DECAY_LAMBDA * max(elapsed_days, 0))
        play.is_liked = play.user_id in liked_user_ids
        play.current_score = current_decay * (LIKE_MULTIPLIER if play.is_liked else 1.0)

    plays.sort(key=lambda p: p.current_score, reverse=True)
    top = plays[:TOP_N]

    previous_ranks = dict(
        SongLeaderboardRank.objects.filter(song_id=song_id).values_list('user_id', 'rank')
    )

    new_rows = []
    for index, play in enumerate(top):
        rank = index + 1
        old_rank = previous_ranks.get(play.user_id)
        if old_rank is None:
            trend = SongLeaderboardRank.Trend.NEW
        elif rank < old_rank:
            trend = SongLeaderboardRank.Trend.UP
        elif rank > old_rank:
            trend = SongLeaderboardRank.Trend.DOWN
        else:
            trend = SongLeaderboardRank.Trend.SAME

        new_rows.append(SongLeaderboardRank(
            song_id=song_id, user_id=play.user_id, rank=rank, score=play.current_score,
            full_listen_count=play.full_listen_count, is_liked=play.is_liked, trend=trend,
        ))

    SongLeaderboardRank.objects.filter(song_id=song_id).delete()
    SongLeaderboardRank.objects.bulk_create(new_rows)

    for row in new_rows:
        row.user = next(p.user for p in top if p.user_id == row.user_id)
    live_user_ids = _current_live_user_ids(song_id)
    entries = [
        _serialize_user(row.user, row.rank, row.trend, row.full_listen_count, row.is_liked, row.user_id in live_user_ids)
        for row in new_rows
    ]
    entries += _live_only_entries(song_id, live_user_ids, {row.user_id for row in new_rows})
    entries = _filter_to_live(entries)

    if broadcast:
        channel_layer = get_channel_layer()
        if channel_layer is not None:
            async_to_sync(channel_layer.group_send)(_group_name(song_id), {
                'type': 'leaderboard.update',
                'entries': entries,
            })

    return entries
