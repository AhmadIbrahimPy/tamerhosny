"""Celery app for background jobs (e.g. the "Sing With Tamer" duet mix -
AI vocal removal + audio mixing is too slow to run in the request/
response cycle of a single-process ASGI server without blocking every
other visitor behind it).

Same Redis instance Channels already uses as its broker - no new
infrastructure, just a second consumer of it.
"""
import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
