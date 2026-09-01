from django.core.management.base import BaseCommand

from backend.media_app.models import CinemaScreening, CinemaVenue, Media


class Command(BaseCommand):
    help = 'Link all media to cinema venues'

    def handle(self, *args, **kwargs):
        # Get all cinema venues
        venues = CinemaVenue.objects.all()
        
        if venues.count() == 0:
            self.stdout.write(self.style.ERROR('No cinema venues found. Please import cinema venues first.'))
            return

        # Get all media (movies)
        media_items = Media.objects.filter(media_type='MOVIE')
        
        if media_items.count() == 0:
            self.stdout.write(self.style.WARNING('No movies found.'))
            return

        linked_count = 0
        skipped_count = 0

        # Link each movie to multiple venues
        for media in media_items:
            # Check if media already has screenings
            existing_screenings = CinemaScreening.objects.filter(media=media).count()

            if existing_screenings > 0:
                self.stdout.write(self.style.WARNING(f'Skipped media (already has screenings): {media.title_ar}'))
                skipped_count += 1
                continue

            # Link to venues in Cairo, Giza, and Alexandria
            egyptian_venues = venues.filter(city__in=['القاهرة', 'الجيزة', 'الإسكندرية'])
            
            if egyptian_venues.count() == 0:
                # If no Egyptian venues, link to all venues
                target_venues = venues
            else:
                target_venues = egyptian_venues

            for venue in target_venues:
                CinemaScreening.objects.create(
                    media=media,
                    venue=venue,
                    ticket_price=150.00,  # Default ticket price
                    booking_url=f'https://tazkarti.com/movie/{media.slug}',
                )
                linked_count += 1

            self.stdout.write(self.style.SUCCESS(f'Linked media to {target_venues.count()} venues: {media.title_ar}'))

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {linked_count} cinema screenings. '
                f'Skipped {skipped_count} media items.'
            )
        )
