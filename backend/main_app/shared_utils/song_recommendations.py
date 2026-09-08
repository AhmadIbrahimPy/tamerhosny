"""Precomputed "songs like this" and "recommended for you" - built from
the same engagement signal as the leaderboard
(backend.main_app.shared_utils.song_leaderboard): each user's decayed
play score per song, boosted for a song they've liked. A song popular
mostly because it's a duet-page novelty or barely played at all falls
back to plain content overlap (shared genre/mood/album/singers) instead.

Plain Python/dict-based rather than numpy/scipy: the catalog here is a
single artist's discography (hundreds, not millions, of songs), so a
sparse item-item cosine similarity over it fits comfortably in memory
and runs fast enough as a nightly batch job, without depending on numpy/
scipy/torch being installed alongside the main web/worker process (today
those are only guaranteed for ai_remix_app's own worker).

Recomputed periodically (see main_app.tasks.refresh_song_recommendations
and the `refresh_recommendations` management command) - not a live
signal, unlike the leaderboard which updates on every full listen.
"""
import math
from collections import defaultdict

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from backend.main_app.shared_utils.song_leaderboard import DECAY_LAMBDA, LIKE_MULTIPLIER

TOP_NEIGHBORS = 20
TOP_RECOMMENDATIONS = 30
MIN_LISTENERS_FOR_COLLABORATIVE = 5
MIN_COLLABORATIVE_NEIGHBORS = 5


def _current_engagement_weights():
    """{song_id: {user_id: weight}} - each user's current (decayed,
    like-boosted) engagement score per song, same math the leaderboard
    uses to rank listeners.
    """
    from backend.main_app.models import Like, UserSongPlay
    from backend.music_app.models import Song

    now = timezone.now()
    song_ct = ContentType.objects.get_for_model(Song)
    liked_pairs = set(
        Like.objects.filter(content_type=song_ct).values_list('user_id', 'object_id')
    )

    weights = defaultdict(dict)
    plays = UserSongPlay.objects.filter(full_listen_count__gt=0).values(
        'user_id', 'song_id', 'decayed_score', 'score_updated_at',
    )
    for play in plays:
        if play['score_updated_at']:
            elapsed_days = (now - play['score_updated_at']).total_seconds() / 86400
            decayed = play['decayed_score'] * math.exp(-DECAY_LAMBDA * max(elapsed_days, 0))
        else:
            decayed = 0.0
        is_liked = (play['user_id'], play['song_id']) in liked_pairs
        score = decayed * (LIKE_MULTIPLIER if is_liked else 1.0)
        if score > 0:
            weights[play['song_id']][play['user_id']] = score
    return weights


def _cosine_similarities(weights):
    """Item-item cosine similarity from {song_id: {user_id: weight}}, via
    a user->songs inverted index so only songs actually co-played by the
    same user are ever compared (no dense all-pairs matrix).

    Returns {song_id: [(other_song_id, score), ...]} - top neighbors,
    desc by score - one entry per song with enough distinct listeners to
    trust collaboratively.
    """
    norms = {
        song_id: math.sqrt(sum(w * w for w in users.values()))
        for song_id, users in weights.items()
    }

    user_songs = defaultdict(list)
    for song_id, users in weights.items():
        for user_id, w in users.items():
            user_songs[user_id].append((song_id, w))

    dot = defaultdict(lambda: defaultdict(float))
    for entries in user_songs.values():
        for i, (song_a, w_a) in enumerate(entries):
            for song_b, w_b in entries[i + 1:]:
                dot[song_a][song_b] += w_a * w_b
                dot[song_b][song_a] += w_a * w_b

    similarities = {}
    for song_id, others in dot.items():
        if len(weights.get(song_id, {})) < MIN_LISTENERS_FOR_COLLABORATIVE:
            continue
        scored = []
        for other_id, d in others.items():
            denom = norms[song_id] * norms[other_id]
            if denom:
                scored.append((other_id, d / denom))
        scored.sort(key=lambda pair: pair[1], reverse=True)
        similarities[song_id] = scored[:TOP_NEIGHBORS]
    return similarities


def _content_neighbors_for(song, all_songs, singers_by_song):
    """Weighted metadata overlap for one song against every other
    candidate - used for cold-start songs the collaborative pass
    couldn't fill (too new/rarely played to have real listening data).
    """
    own_singers = singers_by_song.get(song.pk, set())
    scored = []
    for other in all_songs:
        if other.pk == song.pk:
            continue
        score = 0.0
        if song.album_id and song.album_id == other.album_id:
            score += 3.0
        if song.genre and song.genre == other.genre:
            score += 1.5
        if song.mood and song.mood == other.mood:
            score += 1.0
        if song.song_type == other.song_type:
            score += 0.5
        if own_singers & singers_by_song.get(other.pk, set()):
            score += 2.0
        if score > 0:
            scored.append((other.pk, score))
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:TOP_NEIGHBORS]


def refresh_song_similarities():
    """Recomputes SongSimilarity for every visible, non-duet song:
    collaborative neighbors where there's enough listening data, content-
    based overlap filling in the rest (or the whole list, for a song
    nobody's played yet). Replaces each song's rows wholesale, same
    delete-then-bulk_create pattern as refresh_song_leaderboard.
    """
    from backend.main_app.models import SongSimilarity
    from backend.music_app.models import Song, SongCredit

    songs = list(Song.visible_queryset(Song.objects.filter(is_duet=False)))
    songs_by_id = {song.pk: song for song in songs}

    singers_by_song = defaultdict(set)
    for song_id, person_id in SongCredit.objects.filter(
        song__in=songs, role__in=[SongCredit.Role.SINGER, SongCredit.Role.FEATURED_ARTIST],
    ).values_list('song_id', 'person_id'):
        singers_by_song[song_id].add(person_id)

    weights = _current_engagement_weights()
    collaborative = _cosine_similarities(weights)

    all_rows = []
    for song in songs:
        neighbors = list(collaborative.get(song.pk, []))
        methods = {other_id: SongSimilarity.Method.COLLABORATIVE for other_id, _ in neighbors}

        if len(neighbors) < MIN_COLLABORATIVE_NEIGHBORS:
            have = {other_id for other_id, _ in neighbors}
            for other_id, score in _content_neighbors_for(song, songs, singers_by_song):
                if other_id in have:
                    continue
                neighbors.append((other_id, score))
                methods[other_id] = SongSimilarity.Method.CONTENT
                if len(neighbors) >= TOP_NEIGHBORS:
                    break

        for rank, (other_id, score) in enumerate(neighbors[:TOP_NEIGHBORS], start=1):
            if other_id not in songs_by_id:
                continue
            all_rows.append(SongSimilarity(
                song_id=song.pk, similar_song_id=other_id, score=score,
                method=methods[other_id], rank=rank,
            ))

    SongSimilarity.objects.all().delete()
    SongSimilarity.objects.bulk_create(all_rows)
    return len(all_rows)


def refresh_user_recommendations():
    """Recomputes UserSongRecommendation for every user with real
    listening history: aggregates SongSimilarity across everything
    they've engaged with, weighted by how much they engaged with each
    source song, excluding songs they've already played and anything
    hidden/a duet. Must run after refresh_song_similarities (reads its
    output) - see main_app.tasks.refresh_song_recommendations.
    """
    from backend.main_app.models import SongSimilarity, UserSongRecommendation
    from backend.music_app.models import Song

    weights = _current_engagement_weights()
    user_weights = defaultdict(dict)
    for song_id, users in weights.items():
        for user_id, w in users.items():
            user_weights[user_id][song_id] = w

    visible_song_ids = set(
        Song.visible_queryset(Song.objects.filter(is_duet=False)).values_list('pk', flat=True)
    )

    neighbors_by_song = defaultdict(list)
    for row in SongSimilarity.objects.all().values('song_id', 'similar_song_id', 'score'):
        neighbors_by_song[row['song_id']].append((row['similar_song_id'], row['score']))

    all_rows = []
    for user_id, played in user_weights.items():
        candidate_scores = defaultdict(float)
        for song_id, engagement in played.items():
            for other_id, similarity in neighbors_by_song.get(song_id, []):
                if other_id in played or other_id not in visible_song_ids:
                    continue
                candidate_scores[other_id] += engagement * similarity

        ranked = sorted(candidate_scores.items(), key=lambda pair: pair[1], reverse=True)[:TOP_RECOMMENDATIONS]
        for rank, (song_id, score) in enumerate(ranked, start=1):
            all_rows.append(UserSongRecommendation(
                user_id=user_id, song_id=song_id, score=score, rank=rank,
            ))

    UserSongRecommendation.objects.all().delete()
    UserSongRecommendation.objects.bulk_create(all_rows)
    return len(all_rows)


def refresh_all():
    """Full nightly recompute - similarities first, then per-user
    recommendations (which depend on them)."""
    similarity_count = refresh_song_similarities()
    recommendation_count = refresh_user_recommendations()
    return similarity_count, recommendation_count
