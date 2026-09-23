"""Celery app for background jobs (e.g. the "Sing With Tamer" duet mix -
AI vocal removal + audio mixing is too slow to run in the request/
response cycle of a single-process ASGI server without blocking every
other visitor behind it).

Same Redis instance Channels already uses as its broker - no new
infrastructure, just a second consumer of it.
"""
import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Requires a `celery -A config beat` process running alongside the
# worker - beat is what actually fires scheduled tasks like this one,
# the worker alone only consumes whatever's already queued.
app.conf.beat_schedule = {
    'daily-guess-reminder': {
        'task': 'backend.music_app.tasks.send_daily_guess_reminders',
        'schedule': crontab(hour=18, minute=0),
    },
    'nightly-recommendation-refresh': {
        'task': 'backend.main_app.tasks.refresh_song_recommendations',
        'schedule': crontab(hour=3, minute=0),
    },
    # Catches a "Sing With Tamer" duet stranded in PROCESSING by a
    # worker that died mid-task (OOM, deploy, host reboot) instead of
    # ever reaching create_duet_song's own except block - see
    # requeue_stuck_duet_projects. Runs often since it's a cheap query
    # (an index scan on processing_status + updated_at, no rows most
    # of the time) and a stuck duet should recover within minutes, not
    # sit there until someone notices.
    'requeue-stuck-duet-projects': {
        'task': 'backend.music_app.tasks.requeue_stuck_duet_projects',
        'schedule': 300.0,
    },
    # A duet's shareable video is a disk-hungry, on-demand extra (not
    # the duet itself) - delete it DUET_VIDEO_RETENTION_HOURS after it
    # finished rather than let every generated video accumulate forever.
    'cleanup-expired-duet-videos': {
        'task': 'backend.music_app.tasks.cleanup_expired_duet_videos',
        'schedule': crontab(minute=30),
    },
    # Keeps seed_fake_live_rooms' own fake rooms (management command,
    # backend.main_app) from aging out of ListenTogetherViewer's 90s
    # staleness cutoff - has to run well under that, not just "often
    # enough to feel live". A no-op query when nobody's ever run that
    # command, so always-on here rather than something to toggle.
    'keep-seed-rooms-alive': {
        'task': 'backend.main_app.tasks.keep_seed_rooms_alive',
        'schedule': 60.0,
    },
}
