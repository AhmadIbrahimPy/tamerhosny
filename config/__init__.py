# Makes sure the Celery app is loaded whenever Django starts, so
# @shared_task-decorated tasks (see config/celery.py) always use this app.
from .celery import app as celery_app

__all__ = ('celery_app',)
