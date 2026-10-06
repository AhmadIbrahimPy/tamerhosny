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
