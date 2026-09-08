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
}
