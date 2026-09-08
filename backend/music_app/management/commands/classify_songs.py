import time

from django.core.management.base import BaseCommand

from backend.music_app.models import Song
from backend.music_app.shared_utils.song_classification import classify_and_save


class Command(BaseCommand):
    help = (
        'Backfills genre/mood for every song missing either, via an LLM '
        '(see backend.music_app.shared_utils.song_classification). New '
        'songs get this automatically going forward (see music_app.signals) '
        '- this command is only for the existing backlog.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit', type=int, default=None,
            help='Classify at most this many songs (useful for a quick test run).',
        )
        parser.add_argument(
            '--force', action='store_true',
            help=(
                'Reclassify every song, overwriting genre/mood even where '
                'both are already set - only for correcting a bad bulk '
                'default (e.g. every song sharing the same placeholder '
                'genre/mood from an import), not routine use.'
            ),
        )

    def handle(self, *args, **options):
        force = options['force']
        if force:
            songs = Song.objects.all()
        else:
            from django.db.models import Q
            songs = Song.objects.filter(
                Q(genre='') | Q(genre=Song.Genre.UNSPECIFIED) | Q(mood='') | Q(mood=Song.Mood.UNSPECIFIED)
            )

        if options['limit']:
            songs = songs[:options['limit']]

        total = songs.count()
        changed = 0
        for index, song in enumerate(songs, start=1):
            if classify_and_save(song, force=force):
                changed += 1
                self.stdout.write(f'[{index}/{total}] {song.title_ar} -> {song.genre}/{song.mood}')
            else:
                self.stdout.write(self.style.WARNING(f'[{index}/{total}] {song.title_ar} -> skipped (no provider available)'))
            # A short pause between calls - all three providers are
            # free-tier with per-minute rate limits, and hammering them
            # back-to-back across a whole catalog exhausts each one in
            # turn faster than it would recover, leaving later songs
            # with nothing left to fall back to.
            time.sleep(1.5)

        self.stdout.write(self.style.SUCCESS(f'Classified {changed} of {total} songs.'))
