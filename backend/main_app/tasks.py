"""Celery tasks for main_app: the nightly recommendation recompute (see
config/celery.py's beat_schedule for when it fires) and the voice
assistant's background command-learning analysis.
"""
import random

from celery import shared_task


@shared_task
def refresh_song_recommendations():
    from backend.main_app.shared_utils.song_recommendations import refresh_all

    return refresh_all()


@shared_task
def analyze_failed_voice_command(transcript):
    """Triggered from website_app.views.voice_log whenever the frontend
    reports a COMMAND_FAILED event with an actual transcript - see
    backend.main_app.shared_utils.voice_command_learning for what this
    actually does (classify + generate paraphrases, store as a
    VoiceKnownPhrase for voice_intent() to check on future requests).
    """
    from backend.main_app.shared_utils.voice_command_learning import analyze_and_store

    analyze_and_store(transcript)


@shared_task
def generate_room_name_task(user_id):
    """Fills in a "اسمع معاه" room's AI-generated name after the fact -
    triggered from SongListenerConsumer._start_listening the moment a
    ListenTogetherRoom is first created, never called inline from that
    request. llm_providers.ask_json has no per-call timeout override and
    a worst case of ~135s across its 3 fallback providers - fine for the
    rare/fallback inline callers elsewhere in this codebase (a search
    correction, a voice-intent guess), but this fires on every single
    new room, so it can't block whoever just started listening. The room
    shows ListenTogetherRoom.display_name's own plain fallback
    ("جروب {username}") until this lands, then broadcasts the real name
    to anyone already connected to the room.
    """
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    from backend.main_app.models import ListenTogetherRoom
    from backend.main_app.shared_utils.listen_together import get_current_song_for_user
    from backend.main_app.shared_utils.room_naming import generate_room_name

    room = ListenTogetherRoom.objects.filter(host_id=user_id).select_related('host').first()

    # The room may have already been renamed by the host, or closed
    # (they stopped listening) by the time this runs - never clobber a
    # name the host actually chose, and there's nothing to broadcast to
    # if the room's already gone.
    if room is None or room.custom_name or room.generated_name:
        return

    song = get_current_song_for_user(room.host)
    room.generated_name = generate_room_name(song)
    room.save(update_fields=['generated_name'])

    from backend.main_app.consumers import LiveRoomsFeedConsumer

    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(f'listen_together_{user_id}', {
        'type': 'room.renamed',
        'name': room.display_name,
    })
    # Same gap website_app.views.update_room_settings' own identical
    # second send fixes - a guest on the general feed who hasn't
    # actually joined this room yet has no listen_together_<host>
    # connection to have received the broadcast above, so the AI name
    # landing never reached them there either.
    async_to_sync(channel_layer.group_send)(LiveRoomsFeedConsumer.GROUP_NAME, {
        'type': 'feed.room_renamed',
        'host_user_id': user_id,
        'name': room.display_name,
        'is_public': room.is_public,
    })


@shared_task
def keep_seed_rooms_alive():
    """The 60s-interval beat companion to the seed_fake_live_rooms
    management command - nothing fake ever opens a real WebSocket, so
    nothing would otherwise ever refresh CurrentSongListener/
    ListenTogetherViewer's own last_heartbeat, and the exact same
    staleness sweeps that clean up genuinely abandoned real rooms
    (STALE_LISTENER_CUTOFF=5min, STALE_VIEWER_CUTOFF=90s - consumers.py)
    would eventually take these fake ones down too. Scoped entirely to
    accounts tagged with SEED_EMAIL_DOMAIN - never touches a real
    room/viewer/tap. A no-op (one query, no writes) once nobody's ever
    run that command, so this is safe to leave in the beat schedule
    permanently rather than something to remember to remove.
    """
    from django.db.models import F
    from django.utils import timezone

    from backend.main_app.models import (
        CurrentSongListener, ListenTogetherRoom, ListenTogetherTap, ListenTogetherViewer, UserAccount,
    )
    from backend.main_app.shared_utils.listen_together import SEED_EMAIL_DOMAIN

    seed_user_ids = list(
        UserAccount.objects.filter(email__iendswith=f'@{SEED_EMAIL_DOMAIN}').values_list('id', flat=True)
    )
    if not seed_user_ids:
        return

    now = timezone.now()
    CurrentSongListener.objects.filter(user_id__in=seed_user_ids).update(last_heartbeat=now)
    ListenTogetherViewer.objects.filter(user_id__in=seed_user_ids).update(last_heartbeat=now)
    # Safety net only - shouldn't actually be needed as long as the
    # CurrentSongListener refresh above keeps is_live from ever
    # naturally flipping false in the first place.
    ListenTogetherRoom.objects.filter(host_id__in=seed_user_ids, is_live=False).update(is_live=True)

    # Randomly bumps a handful of rooms' tap_score each cycle, same
    # aggregate+per-user-breakdown update ListenTogetherConsumer._tap
    # does for a real tap - a totally static count sitting there forever
    # would be the one obvious tell that these rooms aren't real.
    rooms = ListenTogetherRoom.objects.filter(host_id__in=seed_user_ids)
    for room in rooms:
        if random.random() > 0.5:
            continue
        viewer_id = (
            ListenTogetherViewer.objects.filter(room=room)
            .order_by('?').values_list('user_id', flat=True).first()
        )
        if viewer_id is None:
            continue
        bump = random.randint(1, 3)
        ListenTogetherRoom.objects.filter(pk=room.pk).update(tap_score=F('tap_score') + bump)
        tap, created = ListenTogetherTap.objects.get_or_create(
            room=room, user_id=viewer_id, defaults={'count': bump},
        )
        if not created:
            ListenTogetherTap.objects.filter(pk=tap.pk).update(count=F('count') + bump)
