"""Seeds fake "اسمع معاه" live rooms so /live-rooms/ (and the homepage's
own slider) never looks dead before real hosts start their own - 5 fake
hosts (Egyptian names, mixed gender), each with a real playable song and
10-50 fake viewers/taps.

Every account this creates - hosts and viewers alike - is tagged with
SEED_EMAIL_DOMAIN (backend.main_app.shared_utils.listen_together), so
they're trivial to find and bulk-delete later in one line:

    UserAccount.objects.filter(email__iendswith='@' + SEED_EMAIL_DOMAIN).delete()

Deliberately NOT enough on its own to keep these rooms "always live" -
the exact same staleness sweeps that clean up genuinely abandoned real
rooms (CurrentSongListener/ListenTogetherViewer's own last_heartbeat
cutoffs, consumers.py) would eventually sweep these fake ones out too,
since nothing here ever opens a real WebSocket to refresh a heartbeat.
backend.main_app.tasks.keep_seed_rooms_alive (config/celery.py's own
beat_schedule, every 60s) is the other half of this - touches every
seeded row's last_heartbeat and randomly bumps tap_score, scoped to the
same email tag.

Idempotent - safe to re-run. Hosts/viewers are matched by a deterministic
email, not recreated each time; rooms/viewer-membership/tap counts are
refreshed in place.
"""
import random
import urllib.request

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db.models import Sum
from django.utils.crypto import get_random_string

from backend.main_app.shared_utils.listen_together import SEED_EMAIL_DOMAIN

# (Arabic display name, Latin username base, is_female) - exactly 5,
# fixed (not randomly sampled) so re-running this command always finds
# the same 5 accounts instead of spawning new ones each time.
HOSTS = [
    ('سارة', 'sara', True),
    ('أحمد', 'ahmed', False),
    ('نور', 'noor', True),
    ('كريم', 'kareem', False),
    ('ياسمين', 'yasmin', True),
]

# Cycled through (with a numeric suffix past the first lap) to build the
# shared viewer pool - real Egyptian first names either way, not
# "fan123"-style placeholders, since these show up as real-looking
# viewer rows in the "الناس في الروم" list.
VIEWER_NAME_POOL = [
    ('سارة', 'sara', True), ('نور', 'noor', True), ('ياسمين', 'yasmin', True),
    ('هبة', 'heba', True), ('مريم', 'mariam', True), ('رنا', 'rana', True),
    ('دينا', 'dina', True), ('فريدة', 'farida', True), ('ملك', 'malak', True),
    ('جنى', 'jana', True), ('حبيبة', 'habiba', True), ('روان', 'rawan', True),
    ('أحمد', 'ahmed', False), ('محمد', 'mohamed', False), ('كريم', 'kareem', False),
    ('يوسف', 'youssef', False), ('عمر', 'omar', False), ('خالد', 'khaled', False),
    ('مصطفى', 'mostafa', False), ('زياد', 'ziad', False), ('حسن', 'hassan', False),
    ('سيف', 'seif', False), ('عادل', 'adel', False), ('طارق', 'tarek', False),
]

# Index-matched to HOSTS (room i gets name i), not picked randomly per
# host - independent random.choice() calls collided ("أغاني وذكريات"
# landed on 3 different hosts the first run), and there's no reason for
# 5 fixed hosts to ever fight over which of 5 fixed names they get.
ROOM_NAMES = ['سهرة ولا أحلى', 'كل يوم تامر', 'مزاج مساء', 'أغاني وذكريات', 'جلسة سمر']

# Verified against https://api.dicebear.com/7.x/avataaars/schema.json -
# a longer/voluminous "top" style reads as feminine, a short one (+ a
# chance of facial hair) as masculine. Cartoon avatars (thStartRoomWithSong
# and every other avatar on this site already falls back to a plain
# letter otherwise), not real photos - nothing here claims to be a real
# person's actual picture.
FEMALE_TOPS = [
    'bigHair', 'bob', 'bun', 'curly', 'curvy', 'frida', 'fro', 'froBand',
    'longButNotTooLong', 'miaWallace', 'straight01', 'straight02', 'straightAndStrand',
]
MALE_TOPS = ['shortFlat', 'shortRound', 'shortCurly', 'shortWaved', 'sides', 'theCaesar', 'theCaesarAndSidePart']
MALE_FACIAL_HAIR = ['beardLight', 'beardMedium', 'moustacheFancy']


def _fetch_avatar_bytes(seed, is_female):
    """Best-effort - profile_image is blank=True/null=True already, so a
    DiceBear hiccup just means that one account keeps the site's normal
    letter-fallback avatar instead of aborting the whole seed run."""
    top = random.choice(FEMALE_TOPS if is_female else MALE_TOPS)
    params = f'seed={seed}&top={top}&size=200'
    if not is_female:
        params += f'&facialHair={random.choice(MALE_FACIAL_HAIR)}&facialHairProbability=75'
    url = f'https://api.dicebear.com/7.x/avataaars/png?{params}'
    try:
        with urllib.request.urlopen(url, timeout=8) as response:
            return response.read()
    except Exception:
        return None


class Command(BaseCommand):
    help = (
        "Seeds 5 fake live 'اسمع معاه' rooms (hosts + 10-50 fake viewers/taps each) "
        "so /live-rooms/ has content from day one. Every account is tagged with "
        "@%s so they're trivial to bulk-delete later." % SEED_EMAIL_DOMAIN
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--viewer-pool', type=int, default=150,
            help='How many fake viewer accounts to create/reuse across the 5 rooms (default 150).',
        )

    def handle(self, *args, **options):
        from backend.main_app.models import (
            CurrentSongListener, ListenTogetherRoom, ListenTogetherTap, ListenTogetherViewer,
        )
        from backend.music_app.models import Song

        songs = list(Song.visible_queryset(Song.objects.exclude(audio_file='')))
        if not songs:
            self.stderr.write(self.style.ERROR('No playable songs found - nothing to start a room with.'))
            return

        hosts = self._make_users(HOSTS, 'host')
        viewers = self._make_users(
            self._viewer_specs(options['viewer_pool']), 'fan',
        )

        for index, host in enumerate(hosts):
            song = random.choice(songs)
            CurrentSongListener.objects.update_or_create(user=host, song=song, defaults={})
            # A stale row for some OTHER song this same host "had playing"
            # on an earlier run would otherwise sit there forever -
            # get_current_song_for_user only ever wants the one current row.
            CurrentSongListener.objects.filter(user=host).exclude(song=song).delete()

            room, _ = ListenTogetherRoom.objects.update_or_create(
                host=host,
                defaults={'is_public': True, 'is_live': True},
            )
            # Always reasserted (not just set-if-empty) - self-heals a
            # name collision from before this fix landed on a re-run,
            # rather than leaving whatever random.choice() had already
            # written stuck there forever.
            desired_name = ROOM_NAMES[index % len(ROOM_NAMES)]
            if room.custom_name != desired_name:
                room.custom_name = desired_name
                room.save(update_fields=['custom_name'])

            room_size = random.randint(10, 50)
            room_viewers = random.sample(viewers, min(room_size, len(viewers)))
            for viewer in room_viewers:
                ListenTogetherViewer.objects.get_or_create(room=room, user=viewer)
                if random.random() < 0.7:
                    ListenTogetherTap.objects.update_or_create(
                        room=room, user=viewer, defaults={'count': random.randint(1, 25)},
                    )

            total_taps = ListenTogetherTap.objects.filter(room=room).aggregate(total=Sum('count'))['total'] or 0
            ListenTogetherRoom.objects.filter(pk=room.pk).update(tap_score=total_taps)

            self.stdout.write(self.style.SUCCESS(
                f'  {host.username}: "{room.display_name}" - {len(room_viewers)} viewers, {total_taps} taps'
            ))

        self.stdout.write(self.style.SUCCESS(
            f'Seeded {len(hosts)} rooms from a pool of {len(viewers)} fake viewers. '
            f'Run "manage.py seed_fake_live_rooms" again any time to refresh room sizes/taps - '
            f'the celery-beat task keep_seed_rooms_alive keeps them from going stale in between.'
        ))

    def _viewer_specs(self, pool_size):
        specs = []
        for i in range(pool_size):
            arabic, latin, is_female = VIEWER_NAME_POOL[i % len(VIEWER_NAME_POOL)]
            lap = i // len(VIEWER_NAME_POOL) + 1
            tag = latin if lap == 1 else f'{latin}{lap}'
            specs.append((arabic, tag, is_female))
        return specs

    def _make_users(self, specs, email_tag):
        from backend.main_app.models import UserAccount

        users = []
        for index, (arabic, latin, is_female) in enumerate(specs, start=1):
            email = f'{latin}.{email_tag}{index}@{SEED_EMAIL_DOMAIN}'
            user = UserAccount.objects.filter(email__iexact=email).first()
            if user is None:
                user = UserAccount.objects.create_user(
                    username=self._unique_username(latin),
                    email=email,
                    password=get_random_string(24),
                    first_name=arabic,
                    role=UserAccount.Role.VIEWER,
                )
                content = _fetch_avatar_bytes(f'{latin}{index}', is_female)
                if content:
                    user.profile_image.save(f'{latin}{index}.png', ContentFile(content), save=True)
            users.append(user)
        return users

    def _unique_username(self, base):
        from backend.main_app.models import UserAccount

        username = base
        n = 1
        while UserAccount.objects.filter(username=username).exists():
            n += 1
            username = f'{base}{n}'
        return username
