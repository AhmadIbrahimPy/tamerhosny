"""Celery tasks for main_app: the nightly recommendation recompute (see
config/celery.py's beat_schedule for when it fires).
"""
from celery import shared_task


@shared_task
def refresh_song_recommendations():
    from backend.main_app.shared_utils.song_recommendations import refresh_all

    return refresh_all()
