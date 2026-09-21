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
from channels.layers import get_channel_layer
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

        if user is not None:
            self._maybe_open_room(user)

    def _stop_listening(self):
        user, session_key = self._identity()

        CurrentSongListener.objects.filter(
            song_id=self.song_id, user=user, session_key=session_key,
        ).delete()

        self.is_listening = False
        self._broadcast_count()
        self._broadcast_live_status()

        if user is not None:
            self._maybe_close_room(user)

    # =========================================================
    # "اسمع معاه" ROOM LIFECYCLE
    #
    # A ListenTogetherRoom exists exactly as long as its host has at
    # least one live CurrentSongListener row, anywhere - not tied to
    # this one song/socket. Switching songs mid-listen briefly stops
    # one CurrentSongListener and starts another (a new socket per song
    # - see connectGlobalListenerSocket in base.html), which would
    # otherwise tear the room down and rebuild it (losing its AI name,
    # re-triggering generation) on every single track change; checking
    # for any OTHER still-live row before closing avoids that churn.
    # =========================================================

    @staticmethod
    def _maybe_open_room(user):
        from backend.main_app.models import ListenTogetherRoom
        from backend.main_app.tasks import generate_room_name_task

        room, created = ListenTogetherRoom.objects.get_or_create(host=user)
        if created:
            generate_room_name_task.delay(user.id)

            # Tells the host's own always-open ListenTogetherConsumer
            # connection (same listen_together_<user.id> group) that
            # hosting just started, so base.html can swap the global
            # player bar into its distinct "hosting" look without a
            # second socket or polling - see room_opened there.
            async_to_sync(get_channel_layer().group_send)(f'listen_together_{user.id}', {
                'type': 'room.opened',
                'tap_score': room.tap_score,
            })

    @staticmethod
    def _maybe_close_room(user):
        from backend.main_app.models import ListenTogetherRoom

        if not CurrentSongListener.objects.filter(user=user).exists():
            deleted, _ = ListenTogetherRoom.objects.filter(host=user).delete()
            if deleted:
                async_to_sync(get_channel_layer().group_send)(f'listen_together_{user.id}', {
                    'type': 'room.closed',
                })

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
            'progress': project.progress_percent,
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
            'progress': event.get('progress'),
        }))


class DuetVideoStatusConsumer(WebsocketConsumer):
    """Progress for one duet's optional shareable video (a Celery task -
    backend.music_app.tasks.create_duet_video), pushed live instead of
    the duet detail page polling /video/status/ on a timer - the render
    can take a couple of minutes, which added up to hundreds of polls
    per render for no benefit over a single open socket. Private to the
    duet's own owner, same rule as DuetProjectStatusConsumer above.
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
        self.group_name = f'duet_video_{project_id}_status'
        async_to_sync(self.channel_layer.group_add)(
            self.group_name, self.channel_name,
        )
        self.accept()

        # In case it already finished (or failed) between the POST that
        # kicked it off and this socket connecting.
        self.send(text_data=json.dumps({
            'type': 'status',
            'status': project.video_status,
            'error': project.video_error,
            'video_url': project.video_file.url if project.video_file else None,
            'progress': project.video_progress_percent,
        }))

    def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            async_to_sync(self.channel_layer.group_discard)(
                self.group_name, self.channel_name,
            )

    def video_status(self, event):
        self.send(text_data=json.dumps({
            'type': 'status',
            'status': event['status'],
            'error': event.get('error', ''),
            'video_url': event.get('video_url'),
            'progress': event.get('progress'),
        }))


class ListenTogetherConsumer(WebsocketConsumer):
    """"اسمع معاه" - live-mirrors one user's ("the host") playback to
    anyone who joins their group from their public profile ("followers").

    One route (ws/listen-together/<host_user_id>/) serves both roles -
    self.is_host tells them apart by comparing the connecting user's own
    id to the host id in the URL. The host's own page opens this exact
    connection to its own id on every page load (see base.html) whether
    or not anyone is actually following, so it's always ready to relay
    playback state and receive a follower_joined ping; followers only
    connect for as long as they're actively listening along.

    No persistent "who's following whom" row - purely a channel-layer
    group (listen_together_<host_user_id>), same presence-only tradeoff
    SongListenerConsumer makes for individual songs. Only the host ever
    sends a 'state' message, so a follower re-broadcasting it back
    upstream (and the feedback loop that would cause) is structurally
    impossible - no extra guarding needed beyond that.

    Public vs. private (ListenTogetherRoom.is_public): a public room (or
    no room row at all - the safe default) behaves exactly as above,
    unchanged. A private room still lets anyone connect - so they can
    receive a live accept/reject - but self.is_approved_follower stays
    False until an ACCEPTED ListenTogetherJoinRequest exists; a pending/
    unapproved connection never gets announced as a follower and never
    receives playback_state. The client has to explicitly send
    {action:'request_join'} - never implicit on connect - so just
    opening the page never files a request on someone's behalf.
    """

    def connect(self):
        user = self.scope.get('user')

        if not user or not user.is_authenticated:
            self.close()
            return

        try:
            host_user_id = int(self.scope['url_route']['kwargs']['host_user_id'])
        except (KeyError, TypeError, ValueError):
            self.close()
            return

        self.user = user
        self.host_user_id = host_user_id
        self.is_host = (user.id == host_user_id)
        self.group_name = f'listen_together_{host_user_id}'
        self.is_approved_follower = True
        # Only ever set True right after _announce_follower_joined()
        # actually runs - disconnect() uses this (not is_host/
        # is_approved_follower alone) to decide whether to broadcast
        # follower.left, since a blocked user's connection sets
        # group_name before being rejected below without ever really
        # joining anything.
        self._joined_announced = False

        if not self.is_host:
            from backend.main_app.models import ListenTogetherBlock, ListenTogetherJoinRequest, ListenTogetherRoom

            is_blocked = ListenTogetherBlock.objects.filter(
                blocker_id=host_user_id, blocked=user,
            ).exists()

            if is_blocked:
                self.close()
                return

            room = ListenTogetherRoom.objects.filter(host_id=host_user_id).first()

            if room is not None and not room.is_public:
                self.is_approved_follower = ListenTogetherJoinRequest.objects.filter(
                    room=room, requester=user,
                    status=ListenTogetherJoinRequest.Status.ACCEPTED,
                ).exists()

        async_to_sync(self.channel_layer.group_add)(
            self.group_name, self.channel_name,
        )
        self.accept()

        if not self.is_host and self.is_approved_follower:
            self._announce_follower_joined()

        if self.is_host:
            self._send_pending_join_requests()
            self._send_current_room_state()

        if self.is_host or self.is_approved_follower:
            self._send_comment_history()

    def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            # Only a connection _announce_follower_joined() actually ran
            # for (a real, counted join) should decrement the host's
            # live join count - group_name gets set before the blocked-
            # user check runs, so hasattr alone isn't enough here.
            if getattr(self, '_joined_announced', False):
                async_to_sync(self.channel_layer.group_send)(self.group_name, {
                    'type': 'follower.left',
                    'user_id': self.user.id,
                })

            async_to_sync(self.channel_layer.group_discard)(
                self.group_name, self.channel_name,
            )

    def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except ValueError:
            return

        action = data.get('action')

        if self.is_host:
            if action == 'state':
                self._broadcast_state(data)
            elif action == 'block':
                self._block(data.get('user_id'))
            elif action == 'respond_join':
                self._respond_join(data.get('user_id'), bool(data.get('approve')))
        elif action == 'request_join':
            self._request_join()

        # Comments and taps are open to any actual participant - the
        # host or an already-approved follower - not gated to one role
        # like the actions above.
        if self.is_host or self.is_approved_follower:
            if action == 'comment':
                self._post_comment(data.get('text'))
            elif action == 'tap':
                self._tap()

    # =========================================================
    # HOST -> GROUP
    # =========================================================

    def _broadcast_state(self, data):
        async_to_sync(self.channel_layer.group_send)(self.group_name, {
            'type': 'playback.state',
            'song': data.get('song'),
            'playing': bool(data.get('playing')),
            'current_time': data.get('currentTime'),
        })

    def _announce_follower_joined(self):
        self._joined_announced = True

        async_to_sync(self.channel_layer.group_send)(self.group_name, {
            'type': 'follower.joined',
            'username': self.user.username,
            'user_id': self.user.id,
        })

        # The one place a join is ever actually confirmed, whether the
        # room is public or this is a private one just approved - a
        # TikTok-style "X انضم" line belongs here and nowhere else, so
        # it can never drift out of sync with the real join logic above.
        self._create_comment(
            kind='system',
            text=f'{self.user.username} انضم',
        )

    # =========================================================
    # COMMENTS + TAPS (host or any approved follower)
    # =========================================================

    def _create_comment(self, kind, text, author=None):
        from backend.main_app.models import ListenTogetherComment, ListenTogetherRoom

        room = ListenTogetherRoom.objects.filter(host_id=self.host_user_id).first()

        if room is None:
            return

        comment = ListenTogetherComment.objects.create(
            room=room, author=author, kind=kind, text=text,
        )

        async_to_sync(self.channel_layer.group_send)(self.group_name, {
            'type': 'comment.posted',
            'id': comment.pk,
            'kind': comment.kind,
            'text': comment.text,
            'author': author.username if author else '',
        })

    def _post_comment(self, text):
        text = (text or '').strip()[:300]

        if not text:
            return

        self._create_comment(kind='message', text=text, author=self.user)

    def _send_comment_history(self):
        from backend.main_app.models import ListenTogetherComment, ListenTogetherRoom

        room = ListenTogetherRoom.objects.filter(host_id=self.host_user_id).first()

        if room is None:
            return

        comments = list(
            ListenTogetherComment.objects.filter(room=room)
            .select_related('author')
            .order_by('-created_at')[:50]
        )
        comments.reverse()

        self.send(text_data=json.dumps({
            'type': 'comment_history',
            'comments': [
                {
                    'id': c.pk,
                    'kind': c.kind,
                    'text': c.text,
                    'author': c.author.username if c.author else '',
                }
                for c in comments
            ],
        }))

    def _tap(self):
        from django.db.models import F

        from backend.main_app.models import ListenTogetherRoom

        updated = ListenTogetherRoom.objects.filter(host_id=self.host_user_id).update(
            tap_score=F('tap_score') + 1,
        )

        if not updated:
            return

        room = ListenTogetherRoom.objects.filter(host_id=self.host_user_id).only('tap_score').first()

        async_to_sync(self.channel_layer.group_send)(self.group_name, {
            'type': 'room.tapped',
            'tap_score': room.tap_score if room else None,
        })

    def _block(self, blocked_user_id):
        from backend.main_app.models import ListenTogetherBlock, UserAccount

        try:
            blocked_user_id = int(blocked_user_id)
        except (TypeError, ValueError):
            return

        blocked_user = UserAccount.objects.filter(pk=blocked_user_id).first()

        if not blocked_user:
            return

        ListenTogetherBlock.objects.get_or_create(
            blocker_id=self.host_user_id, blocked=blocked_user,
        )

        async_to_sync(self.channel_layer.group_send)(self.group_name, {
            'type': 'listener.blocked',
            'user_id': blocked_user_id,
        })

    def _send_pending_join_requests(self):
        """Requests filed while the host wasn't connected (or on a
        previous page) aren't lost - same "resend current state on
        connect" idea DuetProjectStatusConsumer already uses for a
        render that might have finished before its socket opened.
        """
        from backend.main_app.models import ListenTogetherJoinRequest, ListenTogetherRoom

        room = ListenTogetherRoom.objects.filter(host_id=self.host_user_id).first()

        if room is None or room.is_public:
            return

        pending = ListenTogetherJoinRequest.objects.filter(
            room=room, status=ListenTogetherJoinRequest.Status.PENDING,
        ).select_related('requester')

        for req in pending:
            self.send(text_data=json.dumps({
                'type': 'join_requested',
                'username': req.requester.username,
                'user_id': req.requester_id,
            }))

    def _send_current_room_state(self):
        """room.opened only ever fires once, the moment a room is first
        created - a host page-loading (or refreshing) mid-session would
        otherwise never see the player bar switch into hosting mode
        until they stop and start listening again. Same shape as
        room_opened, sent directly instead of via the group.
        """
        from backend.main_app.models import ListenTogetherRoom

        room = ListenTogetherRoom.objects.filter(host_id=self.host_user_id).first()

        if room is None:
            return

        self.send(text_data=json.dumps({
            'type': 'room_opened',
            'tap_score': room.tap_score,
        }))

    # =========================================================
    # FOLLOWER -> GROUP (private rooms only)
    # =========================================================

    def _request_join(self):
        from backend.main_app.models import ListenTogetherJoinRequest, ListenTogetherRoom

        room = ListenTogetherRoom.objects.filter(host_id=self.host_user_id).first()

        if room is None or room.is_public:
            return

        req, created = ListenTogetherJoinRequest.objects.get_or_create(
            room=room, requester=self.user,
            defaults={'status': ListenTogetherJoinRequest.Status.PENDING},
        )

        if not created and req.status != ListenTogetherJoinRequest.Status.PENDING:
            req.status = ListenTogetherJoinRequest.Status.PENDING
            req.save(update_fields=['status'])

        self.send(text_data=json.dumps({'type': 'join_pending'}))

        async_to_sync(self.channel_layer.group_send)(self.group_name, {
            'type': 'join.requested',
            'username': self.user.username,
            'user_id': self.user.id,
        })

        from backend.main_app.models import UserAccount
        from backend.main_app.shared_utils.push_notifications import send_push_to_user

        host = UserAccount.objects.filter(pk=self.host_user_id).first()

        if host:
            send_push_to_user(
                host,
                'طلب انضمام',
                f'{self.user.username} عايز ينضم لجروبك',
            )

    def _respond_join(self, requester_user_id, approve):
        from backend.main_app.models import ListenTogetherJoinRequest, ListenTogetherRoom, UserAccount

        try:
            requester_user_id = int(requester_user_id)
        except (TypeError, ValueError):
            return

        room = ListenTogetherRoom.objects.filter(host_id=self.host_user_id).first()

        if room is None:
            return

        req = ListenTogetherJoinRequest.objects.filter(room=room, requester_id=requester_user_id).first()

        if req is None:
            return

        req.status = (
            ListenTogetherJoinRequest.Status.ACCEPTED if approve
            else ListenTogetherJoinRequest.Status.REJECTED
        )
        req.save(update_fields=['status'])

        async_to_sync(self.channel_layer.group_send)(self.group_name, {
            'type': 'join.approved' if approve else 'join.rejected',
            'user_id': requester_user_id,
        })

        requester = UserAccount.objects.filter(pk=requester_user_id).first()

        if requester:
            from backend.main_app.shared_utils.push_notifications import send_push_to_user

            send_push_to_user(
                requester,
                'اسمع معاه',
                'اتقبلت في الجروب - يلا اسمع!' if approve else 'الطلب اتّرفض',
            )

    # =========================================================
    # GROUP EVENT HANDLERS
    # =========================================================

    def playback_state(self, event):
        if self.is_host or not self.is_approved_follower:
            return

        self.send(text_data=json.dumps({
            'type': 'state',
            'song': event.get('song'),
            'playing': event.get('playing'),
            'currentTime': event.get('current_time'),
        }))

    def follower_joined(self, event):
        if not self.is_host:
            return

        self.send(text_data=json.dumps({
            'type': 'follower_joined',
            'username': event.get('username'),
            'user_id': event.get('user_id'),
        }))

    def follower_left(self, event):
        if not self.is_host:
            return

        self.send(text_data=json.dumps({
            'type': 'follower_left',
            'user_id': event.get('user_id'),
        }))

    def room_opened(self, event):
        if not self.is_host:
            return

        self.send(text_data=json.dumps({
            'type': 'room_opened',
            'tap_score': event.get('tap_score'),
        }))

    def room_closed(self, event):
        # Unlike follower_joined/join_requested/room_opened above, this
        # one isn't host-only - a follower connected to this same group
        # (self.group_name is the host's, shared by both roles) needs to
        # know too, so their own client can stop following and say why
        # instead of just silently going quiet. thIsHostingRoom/
        # thExitHostingMode (host) vs stopListeningWith (follower) is a
        # client-side distinction, not a server-side one - same message
        # either way.
        self.send(text_data=json.dumps({'type': 'room_closed'}))

    def join_requested(self, event):
        if not self.is_host:
            return

        self.send(text_data=json.dumps({
            'type': 'join_requested',
            'username': event.get('username'),
            'user_id': event.get('user_id'),
        }))

    def join_approved(self, event):
        if self.is_host or event.get('user_id') != self.user.id:
            return

        self.is_approved_follower = True
        self.send(text_data=json.dumps({'type': 'join_approved'}))
        # connect() only sends comment history to an ALREADY-approved
        # participant - a private room's requester was still pending
        # back then, so it never got sent; catch up now, before the
        # "X انضم" system line _announce_follower_joined is about to add,
        # so the history renders in the right order on their screen.
        self._send_comment_history()
        self._announce_follower_joined()

    def join_rejected(self, event):
        if self.is_host or event.get('user_id') != self.user.id:
            return

        self.send(text_data=json.dumps({'type': 'join_rejected'}))
        self.close()

    def room_renamed(self, event):
        self.send(text_data=json.dumps({
            'type': 'room_renamed',
            'name': event.get('name'),
        }))

    def comment_posted(self, event):
        if not (self.is_host or self.is_approved_follower):
            return

        self.send(text_data=json.dumps({
            'type': 'comment',
            'id': event.get('id'),
            'kind': event.get('kind'),
            'text': event.get('text'),
            'author': event.get('author'),
        }))

    def room_tapped(self, event):
        if not (self.is_host or self.is_approved_follower):
            return

        self.send(text_data=json.dumps({
            'type': 'tapped',
            'tap_score': event.get('tap_score'),
        }))

    def listener_blocked(self, event):
        if self.is_host or event.get('user_id') != self.user.id:
            return

        self.send(text_data=json.dumps({'type': 'blocked'}))
        self.close()


def _ws_headers(scope):
    return {
        key.decode('latin1').lower(): value.decode('latin1')
        for key, value in scope.get('headers', [])
    }


def _ws_client_ip(scope):
    forwarded = _ws_headers(scope).get('x-forwarded-for')
    if forwarded:
        return forwarded.split(',')[0].strip()
    client = scope.get('client')
    return client[0] if client else None


class AnalyticsTrackConsumer(WebsocketConsumer):
    """Replaces a plain POST per view/play/share/external-click
    (thTrack() in base.html, formerly `fetch('/v1/analytics/track/')`
    on every single call) with one persistent connection per page that
    every tracked event gets sent over instead - the same tab-lifetime
    connection SongListenerConsumer already opens for "who's listening
    now", just carrying a different kind of message. Cuts the
    request-per-event overhead (a full HTTP request, including its own
    TLS/connection setup on a cold keep-alive) down to one handshake for
    the whole page visit.

    Deliberately NOT tied to any one song/page like the other consumers
    here - a single connection covers every event type on every page,
    so the frontend only ever needs to open it once per page load. No
    group_add - nothing broadcasts back out from this one, it's a
    write-only pipe from the browser to a server-side create() per
    message, mirroring TrackHandle.create() (backend.analytics_app.core.
    track) field-for-field so the two stay equivalent. The plain POST
    endpoint stays in place as a fallback for when the socket can't
    connect at all (or a browser too old to support it), not removed.
    """

    def connect(self):
        self.accept()

    def disconnect(self, close_code):
        pass

    def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except (TypeError, ValueError):
            return

        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    self._record_event(item)
        elif isinstance(data, dict):
            self._record_event(data)

    def _record_event(self, data):
        from backend.analytics_app.models import AnalyticsEvent
        from backend.analytics_app.shared_utils.content_types import content_type_for_kind
        from backend.links_app.models import ExternalLink, Platform

        event_type = data.get('event_type')
        kind = data.get('content_type')
        object_id = data.get('object_id')

        if event_type not in AnalyticsEvent.EventType.values:
            return
        content_type = content_type_for_kind(kind)
        if not content_type or not object_id:
            return

        model_class = content_type.model_class()
        if not model_class.objects.filter(pk=object_id).exists():
            return

        platform = None
        external_link = None
        if event_type == AnalyticsEvent.EventType.EXTERNAL_CLICK:
            platform_name = data.get('platform')
            platform = Platform.objects.filter(platform_name=platform_name).first()
            link_id = data.get('external_link_id')
            if link_id:
                external_link = ExternalLink.objects.filter(pk=link_id).first()

        share_channel = ''
        if event_type == AnalyticsEvent.EventType.SHARE:
            share_channel = data.get('share_channel', '')
            if share_channel not in AnalyticsEvent.ShareChannel.values:
                share_channel = AnalyticsEvent.ShareChannel.OTHER

        session = self.scope.get('session')
        session_key = ''
        if session is not None:
            if not session.session_key:
                session.save()
            session_key = session.session_key or ''

        AnalyticsEvent.objects.create(
            event_type=event_type,
            content_type=content_type,
            object_id=object_id,
            platform=platform,
            external_link=external_link,
            share_channel=share_channel,
            session_key=session_key,
            referrer=(data.get('referrer') or '')[:500],
            user_agent=_ws_headers(self.scope).get('user-agent', '')[:255],
            ip_address=_ws_client_ip(self.scope),
        )
