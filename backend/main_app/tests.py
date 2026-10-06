from unittest import mock

from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase, override_settings

from backend.main_app.consumers import SongListenerConsumer
from backend.main_app.models import (
    AudioRoom, AudioRoomParticipant, CurrentSongListener, ListenTogetherRoom, UserAccount,
)
from backend.music_app.models import Song

IN_MEMORY = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}


@override_settings(CHANNEL_LAYERS=IN_MEMORY)
class SongRoomLifecycleTests(TransactionTestCase):
    """A song room opens only on an explicit create (open_room), carries on
    while already live, and never coexists with a voice room."""

    def setUp(self):
        self.user = UserAccount.objects.create(username='host1', email='h1@example.com')
        self.song1 = Song.objects.create(title_ar='s1')
        self.song2 = Song.objects.create(title_ar='s2')
        p = mock.patch('backend.main_app.tasks.generate_room_name_task.delay')
        p.start()
        self.addCleanup(p.stop)

    async def _connect(self, song):
        comm = WebsocketCommunicator(SongListenerConsumer.as_asgi(), f'/ws/songs/{song.pk}/listening/')
        comm.scope['url_route'] = {'kwargs': {'song_id': str(song.pk)}}
        comm.scope['user'] = self.user
        ok, _ = await comm.connect()
        assert ok
        await comm.receive_json_from()
        return comm

    async def _send(self, comm, **data):
        await comm.send_json_to(data)
        await comm.wait_for_close if False else None
        import asyncio
        await asyncio.sleep(0.3)

    @database_sync_to_async
    def _live(self):
        return ListenTogetherRoom.objects.filter(host=self.user, is_live=True).exists()

    async def test_plain_play_does_not_open_room(self):
        c = await self._connect(self.song1)
        await self._send(c, action='start')
        self.assertFalse(await self._live())
        await c.disconnect()

    async def test_explicit_create_opens_room(self):
        c = await self._connect(self.song1)
        await self._send(c, action='start', open_room=True)
        self.assertTrue(await self._live())
        await c.disconnect()

    async def test_song_switch_while_hosting_keeps_room(self):
        c1 = await self._connect(self.song1)
        await self._send(c1, action='start', open_room=True)
        self.assertTrue(await self._live())
        # base.html tears the old socket down before the new one starts
        await c1.disconnect()
        import asyncio
        await asyncio.sleep(0.3)
        c2 = await self._connect(self.song2)
        await self._send(c2, action='start', open_room=True)  # thIsHostingRoom still true
        self.assertTrue(await self._live())
        await c2.disconnect()

    async def test_pause_closes_and_plain_resume_does_not_reopen(self):
        c = await self._connect(self.song1)
        await self._send(c, action='start', open_room=True)
        await self._send(c, action='stop')
        self.assertFalse(await self._live())
        await self._send(c, action='start')
        self.assertFalse(await self._live())
        await c.disconnect()

    async def test_voice_host_or_guest_blocks_song_room(self):
        host = await database_sync_to_async(UserAccount.objects.create)(username='vh', email='vh@example.com')
        room = await database_sync_to_async(AudioRoom.objects.create)(host=host, is_live=True)
        await database_sync_to_async(AudioRoomParticipant.objects.create)(
            room=room, user=self.user, slot_index=1)
        c = await self._connect(self.song1)
        await self._send(c, action='start', open_room=True)
        self.assertFalse(await self._live())
        await c.disconnect()

    async def test_entering_voice_room_closes_own_song_room(self):
        from backend.main_app.consumers import AudioRoomConsumer

        c = await self._connect(self.song1)
        await self._send(c, action='start', open_room=True)
        self.assertTrue(await self._live())

        host = await database_sync_to_async(UserAccount.objects.create)(username='vh2', email='vh2@example.com')
        await database_sync_to_async(AudioRoom.objects.create)(host=host, is_live=True)
        v = WebsocketCommunicator(AudioRoomConsumer.as_asgi(), f'/ws/audio-rooms/{host.pk}/')
        v.scope['url_route'] = {'kwargs': {'host_user_id': str(host.pk)}}
        v.scope['user'] = self.user
        ok, _ = await v.connect()
        self.assertTrue(ok)
        self.assertFalse(await self._live())
        await v.disconnect()
        await c.disconnect()


class AudioRoomPageTests(TransactionTestCase):
    def test_page_renders_with_prev_next_and_controls(self):
        from django.test import Client

        host = UserAccount.objects.create(username='Ahmad', email='a@example.com')
        other = UserAccount.objects.create(username='Other', email='o@example.com')
        viewer = UserAccount.objects.create(username='viewer', email='v@example.com')
        AudioRoom.objects.create(host=host, is_live=True, tap_score=5)
        AudioRoom.objects.create(host=other, is_live=True, tap_score=1)
        c = Client()
        c.force_login(viewer)
        r = c.get('/live-rooms/audio/Ahmad/')
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        for needle in ('thAudioNextBtn', 'thAudioHeartBtn', 'thAudioCommentForm', 'th-room-viewer-badge', 'th-room-name-share-btn'):
            self.assertIn(needle, html)
        # host viewing own room: no up/down nav, no leave-top button
        c.force_login(host)
        html = c.get('/live-rooms/audio/Ahmad/').content.decode()
        self.assertNotIn('id="thAudioNextBtn"', html)


@override_settings(CHANNEL_LAYERS=IN_MEMORY)
class AudioRoomSeatTests(TransactionTestCase):
    """Walk-ins are listeners; seats come only from an approved request or an
    accepted invite (60s), and the host can kick/block anyone instantly."""

    def setUp(self):
        self.host = UserAccount.objects.create(username='boss', email='b@example.com')
        self.guest = UserAccount.objects.create(username='guest', email='g@example.com')
        self.other = UserAccount.objects.create(username='other', email='o2@example.com')
        self.room = AudioRoom.objects.create(host=self.host, is_live=True, max_participants=4)

    async def _join(self, user):
        from backend.main_app.consumers import AudioRoomConsumer

        c = WebsocketCommunicator(AudioRoomConsumer.as_asgi(), f'/ws/audio-room/{self.host.pk}/')
        c.scope['url_route'] = {'kwargs': {'host_user_id': str(self.host.pk)}}
        c.scope['user'] = user
        ok, _ = await c.connect()
        self.assertTrue(ok)
        roster = await self._until(c, 'roster')
        return c, roster

    async def _until(self, comm, type_, timeout=2):
        import asyncio

        end = asyncio.get_event_loop().time() + timeout
        while True:
            left = end - asyncio.get_event_loop().time()
            if left <= 0:
                raise AssertionError(f'never received {type_}')
            msg = await comm.receive_json_from(timeout=left)
            if msg['type'] == type_:
                return msg

    @database_sync_to_async
    def _slot(self, user):
        p = AudioRoomParticipant.objects.filter(room=self.room, user=user).first()
        return p.slot_index if p else 'gone'

    async def test_walk_in_is_a_listener(self):
        h, _ = await self._join(self.host)
        g, roster = await self._join(self.guest)
        self.assertIsNone(roster['youAre']['slotIndex'])
        self.assertIsNone(await self._slot(self.guest))
        await h.disconnect(); await g.disconnect()

    async def test_request_approve_seats_and_broadcasts(self):
        h, _ = await self._join(self.host)
        g, _ = await self._join(self.guest)
        await g.send_json_to({'action': 'request_seat'})
        req = await self._until(h, 'seat_requested')
        self.assertEqual(req['username'], 'guest')
        await h.send_json_to({'action': 'respond_seat', 'requestId': req['requestId'], 'approve': True})
        seated_h = await self._until(h, 'participant_seated')
        seated_g = await self._until(g, 'participant_seated')
        self.assertEqual(seated_h['slotIndex'], 1)
        self.assertEqual(seated_g['userId'], self.guest.pk)
        self.assertEqual(await self._slot(self.guest), 1)
        await h.disconnect(); await g.disconnect()

    async def test_request_rejected(self):
        h, _ = await self._join(self.host)
        g, _ = await self._join(self.guest)
        await g.send_json_to({'action': 'request_seat'})
        req = await self._until(h, 'seat_requested')
        await h.send_json_to({'action': 'respond_seat', 'requestId': req['requestId'], 'approve': False})
        rej = await self._until(g, 'seat_rejected')
        self.assertEqual(rej['reason'], 'rejected')
        self.assertIsNone(await self._slot(self.guest))
        await h.disconnect(); await g.disconnect()

    async def test_request_older_than_60s_cannot_be_approved(self):
        from datetime import timedelta

        from django.utils import timezone

        from backend.main_app.models import AudioRoomSeatRequest

        h, _ = await self._join(self.host)
        g, _ = await self._join(self.guest)
        await g.send_json_to({'action': 'request_seat'})
        req = await self._until(h, 'seat_requested')
        await database_sync_to_async(
            AudioRoomSeatRequest.objects.filter(pk=req['requestId']).update
        )(created_at=timezone.now() - timedelta(seconds=61))
        await h.send_json_to({'action': 'respond_seat', 'requestId': req['requestId'], 'approve': True})
        await self._until(h, 'seat_request_cancelled')
        self.assertIsNone(await self._slot(self.guest))
        await h.disconnect(); await g.disconnect()

    async def test_invite_then_accept(self):
        from channels.layers import get_channel_layer

        layer = get_channel_layer()
        inbox = await layer.new_channel()
        await layer.group_add(f'listen_together_{self.other.pk}', inbox)

        h, _ = await self._join(self.host)
        await h.send_json_to({'action': 'invite', 'userId': self.other.pk})
        sent = await self._until(h, 'invite_sent')
        self.assertEqual(sent['username'], 'other')
        event = await layer.receive(inbox)
        self.assertEqual(event['type'], 'audio.invite')

        o, _ = await self._join(self.other)
        await o.send_json_to({'action': 'accept_invite', 'requestId': event['request_id']})
        seated = await self._until(o, 'participant_seated')
        self.assertEqual(seated['userId'], self.other.pk)
        self.assertEqual(await self._slot(self.other), 1)
        await h.disconnect(); await o.disconnect()

    async def test_invite_only_works_for_the_invited_user(self):
        from channels.layers import get_channel_layer

        layer = get_channel_layer()
        inbox = await layer.new_channel()
        await layer.group_add(f'listen_together_{self.other.pk}', inbox)
        h, _ = await self._join(self.host)
        await h.send_json_to({'action': 'invite', 'userId': self.other.pk})
        event = await layer.receive(inbox)
        g, _ = await self._join(self.guest)
        await g.send_json_to({'action': 'accept_invite', 'requestId': event['request_id']})
        rej = await self._until(g, 'seat_rejected')
        self.assertEqual(rej['reason'], 'expired')
        self.assertIsNone(await self._slot(self.guest))
        await h.disconnect(); await g.disconnect()

    async def test_host_kick_removes_everywhere_and_frees_seat(self):
        h, _ = await self._join(self.host)
        g, _ = await self._join(self.guest)
        o, _ = await self._join(self.other)
        await g.send_json_to({'action': 'request_seat'})
        req = await self._until(h, 'seat_requested')
        await h.send_json_to({'action': 'respond_seat', 'requestId': req['requestId'], 'approve': True})
        await self._until(g, 'participant_seated')

        await h.send_json_to({'action': 'kick', 'target': self.guest.pk})
        await self._until(g, 'kicked')
        left_other = await self._until(o, 'participant_left')
        self.assertEqual(left_other['userId'], self.guest.pk)
        self.assertEqual(await self._slot(self.guest), 'gone')
        await h.disconnect(); await o.disconnect()

    async def test_non_host_cannot_kick(self):
        h, _ = await self._join(self.host)
        g, _ = await self._join(self.guest)
        o, _ = await self._join(self.other)
        await g.send_json_to({'action': 'kick', 'target': self.other.pk})
        import asyncio
        await asyncio.sleep(0.3)
        self.assertNotEqual(await self._slot(self.other), 'gone')
        await h.disconnect(); await g.disconnect(); await o.disconnect()

    async def test_block_kicks_and_refuses_reentry_until_unblocked(self):
        from backend.main_app.consumers import AudioRoomConsumer

        h, _ = await self._join(self.host)
        g, _ = await self._join(self.guest)
        await h.send_json_to({'action': 'block', 'target': self.guest.pk})
        await self._until(g, 'kicked')
        blocked = await self._until(h, 'blocked_list')
        self.assertEqual([u['username'] for u in blocked['users']], ['guest'])

        again = WebsocketCommunicator(AudioRoomConsumer.as_asgi(), f'/ws/audio-room/{self.host.pk}/')
        again.scope['url_route'] = {'kwargs': {'host_user_id': str(self.host.pk)}}
        again.scope['user'] = self.guest
        ok, _ = await again.connect()
        self.assertFalse(ok)

        await h.send_json_to({'action': 'unblock', 'target': self.guest.pk})
        self.assertEqual((await self._until(h, 'blocked_list'))['users'], [])
        g2, _ = await self._join(self.guest)
        await h.disconnect(); await g2.disconnect()

    async def test_stats_and_settings(self):
        h, _ = await self._join(self.host)
        g, _ = await self._join(self.guest)
        await g.send_json_to({'action': 'tap'})
        await g.send_json_to({'action': 'tap'})
        await g.send_json_to({'action': 'comment', 'text': 'hi'})
        while (await self._until(h, 'comment'))['kind'] != 'message':
            pass
        await h.send_json_to({'action': 'get_stats'})
        stats = await self._until(h, 'viewer_stats')
        mine = [x for x in stats['stats'] if x['userId'] == self.guest.pk][0]
        self.assertEqual((mine['taps'], mine['comments']), (2, 1))

        await h.send_json_to({'action': 'update_settings', 'name': 'سهرة', 'isPublic': False})
        upd = await self._until(g, 'settings_updated')
        self.assertEqual((upd['name'], upd['isPublic']), ('سهرة', False))
        # guests can't change settings
        await g.send_json_to({'action': 'update_settings', 'name': 'hack'})
        import asyncio
        await asyncio.sleep(0.3)
        name = await database_sync_to_async(lambda: AudioRoom.objects.get(pk=self.room.pk).custom_name)()
        self.assertEqual(name, 'سهرة')
        await h.disconnect(); await g.disconnect()


@override_settings(CHANNEL_LAYERS=IN_MEMORY)
class HomeLiveStripTests(TransactionTestCase):
    def test_home_strip_lists_voice_rooms_with_kind_chip(self):
        from django.test import Client

        host = UserAccount.objects.create(username='voicehost', email='vh3@example.com')
        AudioRoom.objects.create(host=host, is_live=True, is_public=True, max_participants=6)
        AudioRoom.objects.create(
            host=UserAccount.objects.create(username='hidden', email='hid@example.com'),
            is_live=True, is_public=False,
        )
        html = Client().get('/').content.decode()
        self.assertIn('data-kind="audio"', html)
        self.assertIn('/live-rooms/audio/voicehost/', html)
        self.assertNotIn('/live-rooms/audio/hidden/', html)
        self.assertIn('bi-mic-fill', html)

    async def test_feed_gets_audio_open_and_close_pushes(self):
        from backend.main_app.consumers import (
            AudioRoomConsumer, LiveRoomsFeedConsumer, broadcast_audio_room_opened,
        )

        host = await database_sync_to_async(UserAccount.objects.create)(username='vh4', email='vh4@example.com')
        room = await database_sync_to_async(AudioRoom.objects.create)(host=host, is_live=True, is_public=True)

        feed = WebsocketCommunicator(LiveRoomsFeedConsumer.as_asgi(), '/ws/live-rooms/feed/')
        ok, _ = await feed.connect()
        self.assertTrue(ok)

        await database_sync_to_async(lambda: broadcast_audio_room_opened(AudioRoom.objects.select_related('host').get(pk=room.pk)))()
        opened = await feed.receive_json_from(timeout=2)
        self.assertEqual((opened['type'], opened['room']['hostUsername'], opened['room']['kind']), ('audio_room_opened', 'vh4', 'audio'))

        h = WebsocketCommunicator(AudioRoomConsumer.as_asgi(), f'/ws/audio-room/{host.pk}/')
        h.scope['url_route'] = {'kwargs': {'host_user_id': str(host.pk)}}
        h.scope['user'] = host
        ok, _ = await h.connect()
        self.assertTrue(ok)
        await h.send_json_to({'action': 'end_room'})
        closed = await feed.receive_json_from(timeout=2)
        self.assertEqual((closed['type'], closed['host_user_id']), ('audio_room_closed', host.pk))
        await feed.disconnect()
