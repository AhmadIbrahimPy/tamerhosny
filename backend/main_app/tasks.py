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
