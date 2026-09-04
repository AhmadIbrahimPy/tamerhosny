"""
WebSocket URL routing, site-wide.

New real-time features get their route added here and are wired into
`config/asgi.py`'s single ProtocolTypeRouter - one WebSocket entry
point for the whole site, not one per app.
"""

from django.urls import re_path

from backend.main_app import consumers

websocket_urlpatterns = [
    re_path(
        r'^ws/songs/(?P<song_id>\d+)/listening/$',
        consumers.SongListenerConsumer.as_asgi(),
    ),
    re_path(
        r'^ws/songs/(?P<song_id>\d+)/leaderboard/$',
        consumers.SongLeaderboardConsumer.as_asgi(),
    ),
    re_path(
        r'^ws/duets/(?P<project_id>\d+)/status/$',
        consumers.DuetProjectStatusConsumer.as_asgi(),
    ),
]
