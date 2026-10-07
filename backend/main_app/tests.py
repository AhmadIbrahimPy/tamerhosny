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

    async def test_plain_play_while_in_a_voice_room_never_opens_a_song_room(self):
        host = await database_sync_to_async(UserAccount.objects.create)(username='vh', email='vh@example.com')
        room = await database_sync_to_async(AudioRoom.objects.create)(host=host, is_live=True)
        await database_sync_to_async(AudioRoomParticipant.objects.create)(
            room=room, user=self.user, slot_index=1)
        c = await self._connect(self.song1)
        await self._send(c, action='start')
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


@override_settings(CHANNEL_LAYERS=IN_MEMORY)
class OneRoomAtATimeTests(TransactionTestCase):
    """Song room and voice room never coexist: entering one pulls you out of the other."""

    def setUp(self):
        self.vhost = UserAccount.objects.create(username='vhost', email='vh5@example.com')
        self.me = UserAccount.objects.create(username='me', email='me@example.com')
        self.shost = UserAccount.objects.create(username='shost', email='sh@example.com')
        self.song = Song.objects.create(title_ar='x')
        self.room = AudioRoom.objects.create(host=self.vhost, is_live=True)
        p = mock.patch('backend.main_app.tasks.generate_room_name_task.delay')
        p.start()
        self.addCleanup(p.stop)

    async def _voice_join(self, user, host):
        from backend.main_app.consumers import AudioRoomConsumer

        c = WebsocketCommunicator(AudioRoomConsumer.as_asgi(), f'/ws/audio-room/{host.pk}/')
        c.scope['url_route'] = {'kwargs': {'host_user_id': str(host.pk)}}
        c.scope['user'] = user
        ok, _ = await c.connect()
        self.assertTrue(ok)
        while (await c.receive_json_from(timeout=2))['type'] != 'roster':
            pass
        return c

    async def _follow_song_room(self, user, host):
        from backend.main_app.consumers import ListenTogetherConsumer

        c = WebsocketCommunicator(ListenTogetherConsumer.as_asgi(), f'/ws/listen-together/{host.pk}/')
        c.scope['url_route'] = {'kwargs': {'host_user_id': str(host.pk)}}
        c.scope['user'] = user
        ok, _ = await c.connect()
        self.assertTrue(ok)
        return c

    @database_sync_to_async
    def _in_voice(self, user):
        return AudioRoomParticipant.objects.filter(user=user).exists()

    async def test_following_a_song_room_leaves_the_voice_room(self):
        v = await self._voice_join(self.me, self.vhost)
        self.assertTrue(await self._in_voice(self.me))
        f = await self._follow_song_room(self.me, self.shost)

        seen = []
        while True:
            try:
                seen.append((await v.receive_json_from(timeout=1))['type'])
            except Exception:
                break
            if 'moved' in seen:
                break
        self.assertIn('moved', seen)
        self.assertFalse(await self._in_voice(self.me))
        await f.disconnect()

    async def test_hosting_voice_then_following_song_room_ends_the_voice_room(self):
        v = await self._voice_join(self.vhost, self.vhost)
        f = await self._follow_song_room(self.vhost, self.shost)
        types = []
        while True:
            try:
                types.append((await v.receive_json_from(timeout=1))['type'])
            except Exception:
                break
            if 'room_ended' in types:
                break
        self.assertIn('room_ended', types)
        live = await database_sync_to_async(lambda: AudioRoom.objects.get(pk=self.room.pk).is_live)()
        self.assertFalse(live)
        await f.disconnect()

    async def test_creating_a_song_room_leaves_the_voice_room(self):
        v = await self._voice_join(self.me, self.vhost)
        comm = WebsocketCommunicator(SongListenerConsumer.as_asgi(), f'/ws/songs/{self.song.pk}/listening/')
        comm.scope['url_route'] = {'kwargs': {'song_id': str(self.song.pk)}}
        comm.scope['user'] = self.me
        ok, _ = await comm.connect()
        self.assertTrue(ok)
        await comm.receive_json_from()
        await comm.send_json_to({'action': 'start', 'open_room': True})
        import asyncio
        await asyncio.sleep(0.4)
        self.assertFalse(await self._in_voice(self.me))
        live = await database_sync_to_async(
            lambda: ListenTogetherRoom.objects.filter(host=self.me, is_live=True).exists())()
        self.assertTrue(live)
        await comm.disconnect()


class AudioRoomAdsTests(TransactionTestCase):
    def test_page_carries_live_rooms_ads_and_no_listeners_panel(self):
        import json
        import tempfile

        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.test import Client

        from backend.ads_app.models import Advertisement

        # 1x1 PNG
        png = (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
               b'\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xa7\x9a\xa0\xa0\x00\x00\x00\x00IEND\xaeB`\x82')
        with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
            self._run(png, json, Client, Advertisement, SimpleUploadedFile)

    def _run(self, png, json, Client, Advertisement, SimpleUploadedFile):
        Advertisement.objects.create(
            title='Promo', image=SimpleUploadedFile('x.png', png, 'image/png'), is_active=True,
            external_url='https://example.com', show_on_all_pages=False, placements=['LIVE_ROOMS'],
        )
        Advertisement.objects.create(
            title='Other page only', image=SimpleUploadedFile('y.png', png, 'image/png'), is_active=True,
            show_on_all_pages=False, placements=['HOME'],
        )
        host = UserAccount.objects.create(username='adhost', email='ad@example.com')
        AudioRoom.objects.create(host=host, is_live=True)
        c = Client()
        c.force_login(host)
        html = c.get('/live-rooms/audio/adhost/').content.decode()
        self.assertIn('id="thAudioAdSlot"', html)
        self.assertNotIn('id="thAudioListeners"', html)
        data = html.split('id="thAudioAdsData" type="application/json">')[1].split('</script>')[0]
        titles = [a['title'] for a in json.loads(data)]
        self.assertEqual(titles, ['Promo'])


class LiveRoomsLobbyTests(TransactionTestCase):
    def test_lobby_shows_voice_rooms_even_with_no_song_rooms_and_has_type_switch(self):
        from django.test import Client

        viewer = UserAccount.objects.create(username='lobbyviewer', email='lv@example.com')
        AudioRoom.objects.create(
            host=UserAccount.objects.create(username='voiceonly', email='vo@example.com'),
            is_live=True, is_public=True, custom_name='سهرة',
        )
        c = Client()
        c.force_login(viewer)
        html = c.get('/live-rooms/').content.decode()
        self.assertIn('th-lobby-seg-btn', html)
        self.assertIn('data-tab="songs"', html)
        self.assertIn('data-tab="audio"', html)
        # the voice room is listed on the music lobby too, not "no one's listening"
        self.assertIn('/live-rooms/audio/voiceonly/', html)
        self.assertNotIn('مفيش حد بيسمع دلوقتي - يلا ابدأ انت أول واحد', html)


class TrendingSuggestionTests(TransactionTestCase):
    def setUp(self):
        import tempfile

        from django.core.files.uploadedfile import SimpleUploadedFile

        # The serializer opens the audio file, so it has to really exist.
        self._media = override_settings(MEDIA_ROOT=tempfile.mkdtemp())
        self._media.enable()
        self.addCleanup(self._media.disable)
        self._upload = SimpleUploadedFile('x.mp3', b'ID3' + b'\x00' * 64, 'audio/mpeg')

    def _song(self):
        return Song.objects.create(title_ar='اتحامى فيا', audio_file=self._upload)

    def test_single_trending_song_still_becomes_the_first_suggestion_group(self):
        from types import SimpleNamespace

        from django.test import RequestFactory

        from backend.website_app import views

        song = self._song()
        with mock.patch('backend.main_app.shared_utils.trending.get_trending',
                        return_value=[SimpleNamespace(song=song)]):
            groups = views._suggested_song_groups_for_empty_feed(RequestFactory().get('/'))
        self.assertEqual(groups[0]['mood'], 'TRENDING')
        self.assertEqual([s['songId'] for s in groups[0]['songs']], [song.pk])

    def test_trending_endpoint_for_the_room_song_picker(self):
        from types import SimpleNamespace

        from django.test import Client

        song = self._song()
        with mock.patch('backend.main_app.shared_utils.trending.get_trending',
                        return_value=[SimpleNamespace(song=song)]):
            data = Client().get('/live-rooms/trending-songs/').json()
        self.assertEqual([s['title'] for s in data['songs']], ['اتحامى فيا'])
        self.assertTrue(data['songs'][0]['url'])

    def test_lobby_does_not_claim_no_rooms_when_voice_rooms_are_live(self):
        from django.test import Client

        viewer = UserAccount.objects.create(username='lv2', email='lv2@example.com')
        AudioRoom.objects.create(
            host=UserAccount.objects.create(username='vo2', email='vo2@example.com'),
            is_live=True, is_public=True,
        )
        c = Client()
        c.force_login(viewer)
        html = c.get('/live-rooms/').content.decode()
        self.assertNotIn('مفيش رومات موسيقى شغالة دلوقتي', html)
        self.assertNotIn('مفيش رومات شغالة دلوقتي - ابدأ إنت أول واحد', html)
