"""
WebSocket consumers, site-wide.

SongListenerConsumer replaces the old HTTP-polling "listening now"
feature (5s count poll + 30s heartbeat + a global stale-row sweep that
only ran when someone happened to poll). One WebSocket connection per
song-detail page view now does all of it:

    - Always joins the song's broadcast group on connect, so the
      visitor gets live listener-count push updates with no polling.
    - Only counts as an active listener (a CurrentSongListener row)
      between a 'start' and 'stop' message, which the page sends on
      the <audio> element's play/pause events - same semantics as the
      old start-listening/stop-listening endpoints, just pushed over
      the socket instead of polled.
    - disconnect() is reliable for a normal tab close/navigation, so a
      listener is cleaned up immediately instead of waiting up to 2
      minutes for the next poll's sweep to catch it.
"""

import json
from datetime import timedelta

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from django.utils import timezone

from backend.main_app.models import CurrentSongListener
from backend.music_app.models import Song

# Safety net only: a hard process kill skips disconnect(). Anything
# idle this long is abandoned, not just a slow network.
STALE_LISTENER_CUTOFF = timedelta(minutes=5)


class SongListenerConsumer(WebsocketConsumer):

    def connect(self):
        self.song_id = self.scope['url_route']['kwargs']['song_id']
        self.group_name = f'song_{self.song_id}_listeners'
        self.is_listening = False

        async_to_sync(self.channel_layer.group_add)(
            self.group_name, self.channel_name,
        )
        self.accept()

        self.send(text_data=json.dumps({
            'type': 'count',
            'count': self._current_count(),
        }))

    def disconnect(self, close_code):
        if self.is_listening:
            self._stop_listening()

        async_to_sync(self.channel_layer.group_discard)(
            self.group_name, self.channel_name,
        )

    def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except ValueError:
            return

        action = data.get('action')

        if action == 'start':
            self._start_listening()
        elif action == 'stop':
            self._stop_listening()

    # =========================================================
    # PRESENCE
    # =========================================================

    def _identity(self):
        """(user, session_key) pair identifying this connection."""
        user = self.scope.get('user')

        if user is not None and user.is_authenticated:
            return user, None

        session = self.scope.get('session')

        if session is not None:
            if not session.session_key:
                session.save()
            return None, session.session_key

        return None, None

    def _start_listening(self):
        if not Song.objects.filter(pk=self.song_id).exists():
            return

        user, session_key = self._identity()

        CurrentSongListener.objects.get_or_create(
            song_id=self.song_id, user=user, session_key=session_key,
        )

        self.is_listening = True
        self._broadcast_count()
        self._broadcast_live_status()

    def _stop_listening(self):
        user, session_key = self._identity()

        CurrentSongListener.objects.filter(
            song_id=self.song_id, user=user, session_key=session_key,
        ).delete()

        self.is_listening = False
        self._broadcast_count()
        self._broadcast_live_status()

    def _broadcast_live_status(self):
        # Presence changed but no score changed - just refresh the live
        # dots on the (unchanged) leaderboard, not a full recompute.
        from backend.main_app.shared_utils.song_leaderboard import broadcast_current_leaderboard
        broadcast_current_leaderboard(self.song_id)

    def _current_count(self):
        cutoff = timezone.now() - STALE_LISTENER_CUTOFF

        CurrentSongListener.objects.filter(
            song_id=self.song_id, last_heartbeat__lt=cutoff,
        ).delete()

        return CurrentSongListener.objects.filter(song_id=self.song_id).count()

    def _broadcast_count(self):
        async_to_sync(self.channel_layer.group_send)(self.group_name, {
            'type': 'listener.count',
            'count': self._current_count(),
        })

    # =========================================================
    # GROUP EVENT HANDLER
    # =========================================================

    def listener_count(self, event):
        self.send(text_data=json.dumps({
            'type': 'count',
            'count': event['count'],
        }))


class SongLeaderboardConsumer(WebsocketConsumer):
    """The "top listeners" board on a song's detail page. Read-only from
    the client's side - it joins the song's leaderboard group on connect
    and gets pushed a fresh board whenever a full listen, a like toggle,
    or a presence change (for the live dot) affects it (see
    `backend.main_app.shared_utils.song_leaderboard`).
    """

    def connect(self):
        self.song_id = self.scope['url_route']['kwargs']['song_id']
        self.group_name = f'song_{self.song_id}_leaderboard'

        async_to_sync(self.channel_layer.group_add)(
            self.group_name, self.channel_name,
        )
        self.accept()

        from backend.main_app.shared_utils.song_leaderboard import get_cached_leaderboard
        self.send(text_data=json.dumps({
            'type': 'leaderboard',
            'entries': get_cached_leaderboard(self.song_id),
        }))

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            self.group_name, self.channel_name,
        )

    def leaderboard_update(self, event):
        self.send(text_data=json.dumps({
            'type': 'leaderboard',
            'entries': event['entries'],
        }))


class DuetProjectStatusConsumer(WebsocketConsumer):
    """Progress for one "Sing With Tamer" duet mix - a Celery task
    (backend.music_app.tasks.create_duet_song), too slow to run inline,
    so CreateSongAPIView enqueues it and returns immediately; this is
    how the frontend finds out it actually finished (or failed).
    Private to the project's own owner - it's an unlisted duet, not
    catalog content.
    """

    def connect(self):
        from backend.music_app.models import SingWithTamerProject

        project_id = self.scope['url_route']['kwargs']['project_id']
        user = self.scope.get('user')

        try:
            project = SingWithTamerProject.objects.get(pk=project_id)
        except SingWithTamerProject.DoesNotExist:
            self.close()
            return

        if not user or not user.is_authenticated or project.user_id != user.id:
            self.close()
            return

        self.project_id = project_id
        self.group_name = f'duet_project_{project_id}_status'
        async_to_sync(self.channel_layer.group_add)(
            self.group_name, self.channel_name,
        )
        self.accept()

        # In case it already finished (or failed) between the POST that
        # kicked it off and this socket connecting.
        self.send(text_data=json.dumps({
            'type': 'status',
            'status': project.processing_status,
            'error': project.processing_error,
            'redirect_url': '/my-duets/' if project.is_completed else None,
        }))

    def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            async_to_sync(self.channel_layer.group_discard)(
                self.group_name, self.channel_name,
            )

    def project_status(self, event):
        self.send(text_data=json.dumps({
            'type': 'status',
            'status': event['status'],
            'error': event.get('error', ''),
            'redirect_url': event.get('redirect_url'),
        }))
