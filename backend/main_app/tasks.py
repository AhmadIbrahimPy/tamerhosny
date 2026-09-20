"""Celery tasks for main_app: the nightly recommendation recompute (see
config/celery.py's beat_schedule for when it fires) and the voice
assistant's background command-learning analysis.
"""
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

    async_to_sync(get_channel_layer().group_send)(f'listen_together_{user_id}', {
        'type': 'room.renamed',
        'name': room.display_name,
    })
