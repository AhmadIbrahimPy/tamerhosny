from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from backend.links_app.models import ExternalLink, Platform
from backend.music_app.models import Song


class Command(BaseCommand):
    help = 'Link all songs to streaming platforms'

    def handle(self, *args, **kwargs):
        # Get platforms
        spotify = Platform.objects.filter(platform_name='SPOTIFY').first()
        anghami = Platform.objects.filter(platform_name='ANGHAMI').first()
        apple_music = Platform.objects.filter(platform_name='APPLE_MUSIC').first()
        youtube = Platform.objects.filter(platform_name='YOUTUBE').first()

        if not all([spotify, anghami, apple_music, youtube]):
            self.stdout.write(self.style.ERROR('Some platforms are missing. Please import platforms first.'))
            return

        # Get song content type
        song_content_type = ContentType.objects.get_for_model(Song)

        linked_count = 0
        skipped_count = 0

        # Link all songs to all music platforms
        for song in Song.objects.all():
            # Check if song already has links
            existing_links = ExternalLink.objects.filter(
                content_type=song_content_type,
                object_id=song.pk
            ).count()

            if existing_links > 0:
                self.stdout.write(self.style.WARNING(f'Skipped song (already has links): {song.title_ar}'))
                skipped_count += 1
                continue

            # Create links for each platform
            platforms_data = [
                (spotify, f'https://open.spotify.com/track/{song.slug}'),
                (anghami, f'https://play.anghami.com/song/{song.slug}'),
                (apple_music, f'https://music.apple.com/album/{song.slug}'),
                (youtube, f'https://youtube.com/watch?v={song.slug}'),
            ]

            for platform, url in platforms_data:
                ExternalLink.objects.create(
                    platform=platform,
                    content_type=song_content_type,
                    object_id=song.pk,
                    direct_url=url,
                    access_type='SUBSCRIPTION' if platform.platform_name in ['SPOTIFY', 'APPLE_MUSIC', 'ANGHAMI'] else 'FREE',
                )
                linked_count += 1

            self.stdout.write(self.style.SUCCESS(f'Linked song: {song.title_ar}'))

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {linked_count} links. '
                f'Skipped {skipped_count} songs.'
            )
        )
