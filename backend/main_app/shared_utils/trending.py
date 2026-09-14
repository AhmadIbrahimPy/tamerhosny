"""The site-wide "Trending Now" songs chart.

Modeled on how real streaming-platform charts rank songs: not by raw
lifetime play count (that only ever favors old catalog hits and never
moves), but by *recent* play volume, weighted so a play from an hour ago
counts for more than one from five days ago. A song that's surging right
now outranks one that racked up more total plays spread thin over
months - that's the actual signal "trending" is supposed to capture.

Every real PLAY event (AnalyticsEvent, logged by thTrack('PLAY', ...) on
every genuine playback start - see base.html) within the trending window
counts once, exponentially decayed by its age. The resulting ranking is
diffed against the previous SongTrendingRank rows to produce up/down/
same/new trend arrows, then persisted, replacing the old chart.

There's no Celery/cron worker in this project (confirmed absent), so
recomputation is lazy: get_trending() recomputes only when the stored
chart is older than REFRESH_INTERVAL, triggered by whichever request
happens to hit it first after it goes stale - a normal page view, not a
background job. That keeps the chart fresh without needing new
infrastructure, at the cost of one slightly slower request every hour.
"""
import math

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

TRENDING_WINDOW_DAYS = 7
HALF_LIFE_HOURS = 30.0
DECAY_LAMBDA = math.log(2) / HALF_LIFE_HOURS
TOP_N = 20
REFRESH_INTERVAL_MINUTES = 60
# A song needs at least this many decayed-weighted "points" in the
# window to chart at all - keeps a single stray play from a song nobody
# else is listening to from claiming a trending slot outright.
MIN_SCORE_TO_CHART = 1.5


def _compute_scores():
    from backend.analytics_app.models import AnalyticsEvent
    from backend.music_app.models import Song

    song_ct = ContentType.objects.get_for_model(Song)
    since = timezone.now() - timezone.timedelta(days=TRENDING_WINDOW_DAYS)
    now = timezone.now()

    events = AnalyticsEvent.objects.filter(
        event_type=AnalyticsEvent.EventType.PLAY,
        content_type=song_ct,
        created_at__gte=since,
    ).values_list('object_id', 'created_at')

    scores = {}
    for song_id, created_at in events:
        age_hours = (now - created_at).total_seconds() / 3600
        weight = math.exp(-DECAY_LAMBDA * max(age_hours, 0))
        scores[song_id] = scores.get(song_id, 0.0) + weight

    return scores


def refresh_trending():
    """Recomputes the chart and persists it, returning the new ranking
    as a list of SongTrendingRank instances (already saved), ordered.
    """
    from backend.main_app.models import SongTrendingRank
    from backend.music_app.models import Song

    scores = _compute_scores()
    charting_ids = {
        song_id for song_id, score in scores.items() if score >= MIN_SCORE_TO_CHART
    }

    if charting_ids:
        visible_ids = set(
            Song.visible_queryset(Song.objects.filter(pk__in=charting_ids)).values_list('pk', flat=True)
        )
    else:
        visible_ids = set()

    ranked = sorted(
        ((song_id, scores[song_id]) for song_id in visible_ids),
        key=lambda pair: pair[1],
        reverse=True,
    )[:TOP_N]

    previous_ranks = dict(SongTrendingRank.objects.values_list('song_id', 'rank'))

    new_rows = []
    seen_song_ids = set()
    for index, (song_id, score) in enumerate(ranked, start=1):
        seen_song_ids.add(song_id)
        previous_rank = previous_ranks.get(song_id)
        if previous_rank is None:
            trend = SongTrendingRank.Trend.NEW
        elif index < previous_rank:
            trend = SongTrendingRank.Trend.UP
        elif index > previous_rank:
            trend = SongTrendingRank.Trend.DOWN
        else:
            trend = SongTrendingRank.Trend.SAME

        new_rows.append(SongTrendingRank(
            song_id=song_id,
            rank=index,
            previous_rank=previous_rank,
            score=score,
            trend=trend,
        ))

    SongTrendingRank.objects.exclude(song_id__in=seen_song_ids).delete()
    for row in new_rows:
        SongTrendingRank.objects.update_or_create(
            song_id=row.song_id,
            defaults={
                'rank': row.rank,
                'previous_rank': row.previous_rank,
                'score': row.score,
                'trend': row.trend,
            },
        )

    return SongTrendingRank.objects.select_related('song', 'song__album').order_by('rank')


def get_trending(limit=None):
    """The current chart, recomputing first if it's gone stale. Safe to
    call from any view/template context - the recompute is a handful of
    DB queries over a capped recent window, not a heavy job.
    """
    from backend.main_app.models import SongTrendingRank

    latest = SongTrendingRank.objects.order_by('-updated_at').first()
    is_stale = (
        latest is None
        or (timezone.now() - latest.updated_at) > timezone.timedelta(minutes=REFRESH_INTERVAL_MINUTES)
    )

    if is_stale:
        rows = refresh_trending()
    else:
        rows = SongTrendingRank.objects.select_related('song', 'song__album').order_by('rank')

    return list(rows[:limit]) if limit else list(rows)
