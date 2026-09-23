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
            self._maybe_close_room(user.id)

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

        # created is only ever True the very first time this host has
        # hosted, period - the row itself now outlives any one listening
        # session (see is_live's own docstring), so it can't be reused
        # as "did a room just genuinely (re)start" the way it used to.
        # is_live's own False->True transition is that signal instead -
        # True already (still mid-session, this call is just a song
        # switch mid-hosting) means none of this needs to run again.
        if not room.is_live:
            room.is_live = True
            room.save(update_fields=['is_live'])

            # A fresh session starts with an empty comment list, not
            # whatever "X انضم"/chat history piled up from before this
            # host last paused - the room ROW surviving a pause is what
            # keeps its name/tap_score, but comments are tied to one
            # live session, not the room's whole lifetime.
            from backend.main_app.models import ListenTogetherComment

            ListenTogetherComment.objects.filter(room=room).delete()

            # Tells the host's own always-open ListenTogetherConsumer
            # connection (same listen_together_<user.id> group) that
            # hosting just started, so base.html can swap the global
            # player bar into its distinct "hosting" look without a
            # second socket or polling - see room_opened there. Also
            # reaches any already-connected follower now (room_opened
            # used to be host-only) - live_rooms.html's own slide was
            # otherwise stuck showing "الروم اتقفلت" forever once the
            # host paused and resumed, with no signal telling it the
            # room was actually back.
            async_to_sync(get_channel_layer().group_send)(f'listen_together_{user.id}', {
                'type': 'room.opened',
                'tap_score': room.tap_score,
            })

            # Separately, anyone sitting on the general /live-rooms/
            # feed with nothing to show yet gets this room pushed to
            # them live - previously they only ever found out on their
            # next manual page load. See LiveRoomsFeedConsumer and
            # live_rooms.html's own 'room_opened' handler (not to be
            # confused with the host-only event of the same name just
            # above - different group, different payload shape). Private
            # rooms are pushed too, same as website_app.views.live_rooms'
            # own query no longer filtering them out - live_rooms.html's
            # blurred "طلب انضمام" overlay is exactly what handles one of
            # these once it lands (thAddLiveRoomSlide -> thBuildSlide).
            from backend.main_app.shared_utils.listen_together import (
                get_current_song_for_user,
                serialize_song_for_listen_together,
            )

            song = get_current_song_for_user(user)
            if song is not None:
                async_to_sync(get_channel_layer().group_send)(
                    LiveRoomsFeedConsumer.GROUP_NAME, {
                        'type': 'feed.room_opened',
                        'room': {
                            'hostUserId': user.id,
                            'hostUsername': user.username,
                            'hostAvatar': user.profile_image.url if user.profile_image else '',
                            'roomName': room.display_name,
                            'isPublic': room.is_public,
                            'tapScore': room.tap_score,
                            'song': serialize_song_for_listen_together(song),
                        },
                    },
                )

    @staticmethod
    def _maybe_close_room(user_id):
        """Takes a plain id, not a user instance - callable both from
        _stop_listening (a specific connection's own user) and from
        _current_count's sweep below (which only ever has ids on hand,
        for whichever OTHER users' rows it just swept away, not full
        objects worth fetching just for this)."""
        from backend.main_app.models import ListenTogetherRoom

        # Same STALE_LISTENER_CUTOFF every other read of this table
        # already respects (_current_count below, get_current_song_for_
        # user) - without it, a row this user never got to clean up
        # themselves (a hard process kill, e.g. a deploy restarting the
        # ASGI workers mid-connection, skips disconnect() same as this
        # module's own docstring already warns) sits there forever and
        # permanently blocks this from ever seeing "zero rows left" again -
        # "إنهاء" (or just genuinely stopping) looked like it silently did
        # nothing, every single time, for as long as that one phantom row
        # from some other song existed.
        cutoff = timezone.now() - STALE_LISTENER_CUTOFF
        # Swept here too (not just excluded from the check below) - the
        # per-song sweep in _current_count only ever runs for whichever
        # song someone happens to still be querying, so a row like this
        # one (some OTHER, no-longer-visited song) could otherwise sit in
        # the table forever even though it's already being ignored.
        CurrentSongListener.objects.filter(user_id=user_id, last_heartbeat__lt=cutoff).delete()
        if not CurrentSongListener.objects.filter(user_id=user_id).exists():
            # The row itself stays - only is_live flips off - so a
            # custom name, generated_name, and tap_score all survive a
            # host just pausing/switching devices for a bit instead of
            # resetting to a brand new room (new random fallback name
            # included) the moment they press play again.
            updated = ListenTogetherRoom.objects.filter(host_id=user_id, is_live=True).update(is_live=False)
            if updated:
                async_to_sync(get_channel_layer().group_send)(f'listen_together_{user_id}', {
                    'type': 'room.closed',
                })
                async_to_sync(get_channel_layer().group_send)(
                    LiveRoomsFeedConsumer.GROUP_NAME, {
                        'type': 'feed.room_closed',
                        'host_user_id': user_id,
                    },
                )

    def _broadcast_live_status(self):
        # Presence changed but no score changed - just refresh the live
        # dots on the (unchanged) leaderboard, not a full recompute.
        from backend.main_app.shared_utils.song_leaderboard import broadcast_current_leaderboard
        broadcast_current_leaderboard(self.song_id)

    def _current_count(self):
        cutoff = timezone.now() - STALE_LISTENER_CUTOFF

        stale = CurrentSongListener.objects.filter(
            song_id=self.song_id, last_heartbeat__lt=cutoff,
        )
        # Whoever's rows are about to be swept, before they're gone -
        # this is the ONLY place a stale row for someone who never came
        # back to cleanly stop/disconnect ever gets noticed at all. Not
        # re-checking their room here left it stuck is_live=True forever
        # with zero rows behind it (this exact drift is what made a
        # later _maybe_open_room think "nothing changed, no reason to
        # tell anyone" the next time that same host actually started
        # playing again - a follower's slide never got the room_opened
        # that would have un-paused it).
        stale_user_ids = list(
            stale.exclude(user_id=None).values_list('user_id', flat=True).distinct()
        )
        stale.delete()

        for user_id in stale_user_ids:
            self._maybe_close_room(user_id)

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


class LiveRoomsFeedConsumer(WebsocketConsumer):
    """Anyone sitting on the general /live-rooms/ feed (see
    website_app.views.live_rooms) joins this one group for as long as
    the page is open - a live push the instant a new public room opens
    or an existing one closes, instead of only ever finding out on the
    visitor's next manual page load (see SongListenerConsumer's own
    _maybe_open_room/_maybe_close_room, the only senders into this
    group). Purely server-to-client - nothing it ever expects to
    receive.
    """

    GROUP_NAME = 'live_rooms_feed'

    def connect(self):
        async_to_sync(self.channel_layer.group_add)(self.GROUP_NAME, self.channel_name)
        self.accept()

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(self.GROUP_NAME, self.channel_name)

    def feed_room_opened(self, event):
        self.send(text_data=json.dumps({'type': 'room_opened', 'room': event['room']}))

    def feed_room_closed(self, event):
        self.send(text_data=json.dumps({'type': 'room_closed', 'host_user_id': event['host_user_id']}))

    def feed_room_renamed(self, event):
        # A rename/visibility change (website_app.views.update_room_
        # settings) only ever broadcast to the room's own listen_
        # together_<host> group before - reached anyone actively
        # following (or waiting on a private room's response), but not
        # a guest sitting on this general feed who hasn't tapped "طلب
        # انضمام" yet, since that guest has no connection to that group
        # at all until they do. This group is the one connection every
        # visitor on /live-rooms/ already has open regardless.
        self.send(text_data=json.dumps({
            'type': 'room_renamed',
            'host_user_id': event['host_user_id'],
            'name': event['name'],
            'is_public': event['is_public'],
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


# Safety net only, same reasoning as STALE_LISTENER_CUTOFF above - a
# normal tab close/navigation already runs disconnect() reliably. Tighter
# than that one (viewers ping every 25s from thFollowSocket, see
# base.html, vs. song listeners' much lower-frequency traffic) so a
# genuinely gone viewer clears from "الناس في الروم" reasonably quickly
# instead of sitting there for minutes.
STALE_VIEWER_CUTOFF = timedelta(seconds=90)


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

        if self.is_host:
            self._send_pending_join_requests()
            self._send_current_room_state()
            # Without this, a host who just reloaded/reconnected mid-
            # session (thConnectListenTogetherHost reconnects on every
            # fresh page load) started back at thFollowers=[] client-
            # side and only rebuilt the count from whatever
            # follower_joined/left happened to arrive AFTER that -
            # anyone who joined earlier and never left was invisible to
            # them until someone else's join/leave nudged the number.
            self._send_viewers_snapshot()

        # History has to go out BEFORE the join announcement below, not
        # after - _announce_follower_joined's own group_send reaches
        # this exact connection too (already in the group via group_add
        # above), so sending history second used to include the "X
        # انضم" comment it had just created, and the live broadcast
        # delivered that same comment a second time - the joiner saw it
        # twice, everyone else already in the room only once.
        if self.is_host or self.is_approved_follower:
            self._send_comment_history()
            # Sent BEFORE _announce_follower_joined() below (which is
            # the thing that actually adds this exact connection's own
            # row) - a fresh connection's baseline should be "everyone
            # already here", with its own join arriving right after as
            # the first live delta on top of that, not counted twice.
            self._send_viewers_snapshot()

        if not self.is_host and self.is_approved_follower:
            self._announce_follower_joined()

    def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            # Only a connection _announce_follower_joined() actually ran
            # for (a real, counted join) should decrement the host's
            # live join count - group_name gets set before the blocked-
            # user check runs, so hasattr alone isn't enough here.
            if getattr(self, '_joined_announced', False):
                from backend.main_app.models import ListenTogetherViewer

                ListenTogetherViewer.objects.filter(
                    room__host_id=self.host_user_id, user=self.user,
                ).delete()

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
            elif action == 'end_room':
                self._end_room()
        elif action == 'request_join':
            self._request_join()
        elif action == 'cancel_join':
            self._cancel_join()

        # Comments and taps are open to any actual participant - the
        # host or an already-approved follower - not gated to one role
        # like the actions above.
        if self.is_host or self.is_approved_follower:
            if action == 'comment':
                self._post_comment(data.get('text'))
            elif action == 'tap':
                self._tap()
            elif action == 'heartbeat':
                self._heartbeat()

    # =========================================================
    # HOST -> GROUP
    # =========================================================

    def _broadcast_state(self, data):
        playing = bool(data.get('playing'))
        song_data = data.get('song') or {}

        # thSendListenTogetherMessage fires this on every songChanged/
        # audioPlayPause AND a throttled timeupdate ping while the same
        # song keeps playing - self._credited_song_id (per-connection,
        # not persisted) is how a "new song actually started" is told
        # apart from "still the same song, just another progress tick",
        # so a room full of viewers only gets credited with one listen
        # per song, not once per throttle tick.
        song_id = song_data.get('songId')
        if playing and song_id and song_id != getattr(self, '_credited_song_id', None):
            self._credited_song_id = song_id
            self._credit_room_play(song_id)
        elif not playing:
            self._credited_song_id = None

        async_to_sync(self.channel_layer.group_send)(self.group_name, {
            'type': 'playback.state',
            'song': song_data,
            'playing': playing,
            'current_time': data.get('currentTime'),
        })

    def _credit_room_play(self, song_id):
        """Counts the song the host just started as one listen for every
        person actually in the room right now - the host themselves plus
        everyone in ListenTogetherViewer - not just the host's own
        browser (the only one that would otherwise ever reach
        increment_play_count, since followers never call it - see
        base.html's th-following-room guard on the 'play' listener)."""
        from backend.main_app.models import ListenTogetherRoom, ListenTogetherViewer
        from backend.main_app.shared_utils.listen_together import record_song_play

        try:
            song = Song.objects.get(pk=song_id)
        except (Song.DoesNotExist, ValueError, TypeError):
            return

        record_song_play(self.user, song)

        room = ListenTogetherRoom.objects.filter(host_id=self.host_user_id).first()
        if room is not None:
            for viewer_user in [
                v.user for v in ListenTogetherViewer.objects.filter(room=room).select_related('user')
            ]:
                record_song_play(viewer_user, song)

    def _end_room(self):
        # live_rooms.html's own "إنهاء" button - the only thing that
        # actually sends this. Deliberately separate from the ordinary
        # room_closed a plain pause already produces (see
        # SongListenerConsumer._maybe_close_room - is_live tracks "is
        # something actually playing right now", so pausing your own
        # song closes the room the exact same way): a follower's slide
        # used to show the full "this room is over, go find another one"
        # treatment for BOTH, which made a host just pausing for a
        # second look permanently over. is_live/CurrentSongListener
        # cleanup itself still goes through the normal stop path (the
        # client sends this alongside, not instead of, stopping playback)
        # - this is purely an extra "and this one's for real" signal.
        async_to_sync(self.channel_layer.group_send)(self.group_name, {
            'type': 'room.ended',
        })

    def _announce_follower_joined(self):
        from backend.main_app.models import ListenTogetherRoom, ListenTogetherViewer

        self._joined_announced = True

        room = ListenTogetherRoom.objects.filter(host_id=self.host_user_id).first()
        if room is not None:
            # The one authoritative record of "who's actually in this
            # room right now" - see ListenTogetherViewer's own docstring
            # for why every client needs to read from this instead of
            # just accumulating follower_joined/left events from
            # whenever THEIR OWN connection happened to open.
            viewer, created = ListenTogetherViewer.objects.get_or_create(room=room, user=self.user)
            if created:
                # Joining mid-song still counts as a listen, same as
                # anyone already in the room got credited for when the
                # host started it (_credit_room_play) - otherwise
                # someone who joins seconds after a song starts and
                # leaves before the next one would never be counted at
                # all.
                from backend.main_app.shared_utils.listen_together import (
                    get_current_song_for_user, record_song_play,
                )

                current_song = get_current_song_for_user(room.host)
                if current_song is not None:
                    record_song_play(self.user, current_song)
            if not created:
                # get_or_create's own save() only runs (bumping
                # last_heartbeat via auto_now) on the CREATE path - a
                # reconnect finding an existing row (backgrounded tab,
                # brief network drop) needs this explicit touch too, or
                # a viewer who's been away for a while would reconnect
                # only to have _sweep_stale_viewers evict them moments
                # later anyway, before their own heartbeat loop got a
                # chance to run.
                ListenTogetherViewer.objects.filter(pk=viewer.pk).update(last_heartbeat=timezone.now())

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

    def _send_viewers_snapshot(self):
        from backend.main_app.models import ListenTogetherRoom, ListenTogetherViewer

        room = ListenTogetherRoom.objects.filter(host_id=self.host_user_id).first()
        if room is None:
            viewers = []
        else:
            # Swept here too, not just from the periodic heartbeat below -
            # every fresh connection (host reconnecting, a new follower
            # joining) reads this, so a stale row never has to wait for
            # someone else's heartbeat to happen to land before it stops
            # showing up as still "in the room".
            self._sweep_stale_viewers(room)
            viewers = [
                {'user_id': v.user_id, 'username': v.user.username}
                for v in ListenTogetherViewer.objects.filter(room=room).select_related('user')
            ]

        self.send(text_data=json.dumps({
            'type': 'viewers_snapshot',
            'viewers': viewers,
        }))

    def _heartbeat(self):
        # Host has no ListenTogetherViewer row of its own (it's not a
        # "viewer" of itself) - nothing to touch, and no room to sweep
        # on behalf of that isn't already covered by every OTHER
        # follower's own heartbeat/join/reconnect in that same room.
        if self.is_host:
            return

        from backend.main_app.models import ListenTogetherRoom

        room = ListenTogetherRoom.objects.filter(host_id=self.host_user_id).first()
        if room is None:
            return

        from backend.main_app.models import ListenTogetherViewer

        ListenTogetherViewer.objects.filter(room=room, user=self.user).update(
            last_heartbeat=timezone.now(),
        )
        self._sweep_stale_viewers(room)

    def _sweep_stale_viewers(self, room):
        """Deletes any ListenTogetherViewer row for `room` that's gone
        quiet past STALE_VIEWER_CUTOFF and tells the group they left -
        the lazy, read-triggered safety net for whatever skipped
        disconnect() (see ListenTogetherViewer.last_heartbeat's own
        docstring), same pattern SongListenerConsumer._maybe_close_room
        already uses for CurrentSongListener. Broadcasting follower.left
        for each one (not just silently deleting) is what actually
        clears them from anyone ELSE's already-open "الناس في الروم"
        list too, not just the next snapshot request's."""
        from backend.main_app.models import ListenTogetherViewer

        cutoff = timezone.now() - STALE_VIEWER_CUTOFF
        stale = ListenTogetherViewer.objects.filter(room=room, last_heartbeat__lt=cutoff)
        stale_user_ids = list(stale.values_list('user_id', flat=True))
        if not stale_user_ids:
            return

        stale.delete()
        for user_id in stale_user_ids:
            async_to_sync(self.channel_layer.group_send)(self.group_name, {
                'type': 'follower.left',
                'user_id': user_id,
            })

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
            'authorAvatar': author.profile_image.url if author and author.profile_image else '',
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
                    'authorAvatar': c.author.profile_image.url if c.author and c.author.profile_image else '',
                }
                for c in comments
            ],
        }))

    def _tap(self):
        from django.db.models import F

        from backend.main_app.models import ListenTogetherRoom, ListenTogetherTap

        updated = ListenTogetherRoom.objects.filter(host_id=self.host_user_id).update(
            tap_score=F('tap_score') + 1,
        )

        if not updated:
            return

        room = ListenTogetherRoom.objects.filter(host_id=self.host_user_id).only('tap_score').first()

        # Per-user breakdown, separate from the room's own aggregate
        # tap_score just updated above - only the host ever reads this
        # (the viewers popup, live_rooms.html), to see who's actually
        # engaged rather than just a total count.
        tap_row, tap_created = ListenTogetherTap.objects.get_or_create(
            room=room, user=self.user, defaults={'count': 1},
        )
        if not tap_created:
            ListenTogetherTap.objects.filter(pk=tap_row.pk).update(count=F('count') + 1)

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
                # Best-effort - live_rooms.html's own join-requests list
                # (thRenderJoinRequestsList) uses this to show the host a
                # live countdown matching the requester's own, not just a
                # bare name with no sense of how long it's been pending.
                'started_at': req.created_at.isoformat(),
            }))

    def _send_current_room_state(self):
        """room.opened only ever fires once, the moment a room is first
        created - a host page-loading (or refreshing) mid-session would
        otherwise never see the player bar switch into hosting mode
        until they stop and start listening again. Same shape as
        room_opened, sent directly instead of via the group.

        is_live=True is required here - the row itself outlives any one
        session (see ListenTogetherRoom.is_live's own docstring), so
        without this, ANYONE who has ever hosted so much as once got the
        player bar's hosting mode falsely re-activated on literally every
        future page load/reconnect (thConnectListenTogetherHost runs on
        every one), whether they were actually live at that moment or
        not - "بتستضيف جروب دلوقتي" showing with 0 listeners for a room
        that wasn't really open, right after just leaving someone ELSE's
        room and refreshing.
        """
        from backend.main_app.models import ListenTogetherRoom

        room = ListenTogetherRoom.objects.filter(host_id=self.host_user_id, is_live=True).first()

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

        # "Now", not req.created_at - a retry after an earlier expiry/
        # rejection reuses the same row (created_at is auto_now_add,
        # never updated), but the 60s window a host's own countdown
        # should track starts fresh with THIS attempt, not whenever the
        # row first ever existed.
        started_at = timezone.now()

        async_to_sync(self.channel_layer.group_send)(self.group_name, {
            'type': 'join.requested',
            'username': self.user.username,
            'user_id': self.user.id,
            'started_at': started_at.isoformat(),
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

    def _cancel_join(self):
        """The requester's own 60s countdown (live_rooms.html) ran out
        with no response - tells the host to drop it from their pending
        list in real time, instead of it just sitting there until they
        happen to notice it's stale. Only ever touches a still-PENDING
        row of this exact requester's own - a request the host already
        acted on (or one for a room that went public/private again in
        the meantime) is left alone."""
        from backend.main_app.models import ListenTogetherJoinRequest, ListenTogetherRoom

        room = ListenTogetherRoom.objects.filter(host_id=self.host_user_id).first()

        if room is None:
            return

        updated = ListenTogetherJoinRequest.objects.filter(
            room=room, requester=self.user,
            status=ListenTogetherJoinRequest.Status.PENDING,
        ).update(status=ListenTogetherJoinRequest.Status.EXPIRED)

        if updated:
            async_to_sync(self.channel_layer.group_send)(self.group_name, {
                'type': 'join.expired',
                'user_id': self.user.id,
            })

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
        # Used to be host-only (the follower chip/join count on the
        # global bar). live_rooms.html's own live viewer-count badge
        # (any room's slide, not just your own) needs this too now -
        # same reasoning as room_opened/room_closed above, not gated to
        # one role.
        self.send(text_data=json.dumps({
            'type': 'follower_joined',
            'username': event.get('username'),
            'user_id': event.get('user_id'),
        }))

    def follower_left(self, event):
        self.send(text_data=json.dumps({
            'type': 'follower_left',
            'user_id': event.get('user_id'),
        }))

    def room_opened(self, event):
        # Used to be host-only (swap the global bar into hosting mode) -
        # a follower whose room just paused-and-resumed needs this too
        # now, to know the room is actually back (see
        # thHandleRoomClosedOnSlide's own un-close counterpart,
        # live_rooms.html), not just the host.
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

    def room_ended(self, event):
        # See _end_room's own docstring - sent once, right when "إنهاء"
        # is pressed, ahead of (not instead of) the ordinary room_closed
        # the actual stop-listening still triggers a moment later.
        self.send(text_data=json.dumps({'type': 'room_ended'}))

    def join_requested(self, event):
        if not self.is_host:
            return

        self.send(text_data=json.dumps({
            'type': 'join_requested',
            'username': event.get('username'),
            'user_id': event.get('user_id'),
            'started_at': event.get('started_at'),
        }))

    def join_expired(self, event):
        # Host-only, same as join_requested above - the requester who
        # sent this already knows their own request just timed out
        # (that's what drove the client-side countdown that sent it),
        # they don't need it echoed back to themselves.
        if not self.is_host:
            return

        self.send(text_data=json.dumps({
            'type': 'join_expired',
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
        self._send_viewers_snapshot()
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
            'is_public': event.get('is_public'),
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
            'authorAvatar': event.get('authorAvatar'),
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
