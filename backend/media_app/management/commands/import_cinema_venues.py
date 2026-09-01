from django.core.management.base import BaseCommand

from backend.media_app.models import CinemaVenue


class Command(BaseCommand):
    help = 'Import cinema venues in Egypt'

    def handle(self, *args, **kwargs):
        # Cinema venues data - Egypt
        venues_data = {
            # Cairo
            'سينما جالاكسي': {
                'city': 'القاهرة',
            },
            'راديو سينما': {
                'city': 'القاهرة',
            },
            'سينما زهرية': {
                'city': 'القاهرة',
            },
            'سينما ستارز': {
                'city': 'القاهرة',
            },
            'سينما كارو': {
                'city': 'القاهرة',
            },
            'سينما ريفولي': {
                'city': 'القاهرة',
            },
            'سينما ديانا': {
                'city': 'القاهرة',
            },
            'سينما أمباسادور': {
                'city': 'القاهرة',
            },
            # Giza
            'سينما فيستيفال': {
                'city': 'الجيزة',
            },
            'سينما أوربت': {
                'city': 'الجيزة',
            },
            'سينما جالاكسي الجيزة': {
                'city': 'الجيزة',
            },
            'سينما الدقي': {
                'city': 'الجيزة',
            },
            'سينما المهندسين': {
                'city': 'الجيزة',
            },
            # Alexandria
            'سينما ايمر': {
                'city': 'الإسكندرية',
            },
            'سان استيفنو': {
                'city': 'الإسكندرية',
            },
            'سينما رويال': {
                'city': 'الإسكندرية',
            },
            'سينما رامليس': {
                'city': 'الإسكندرية',
            },
            'سينما ميامي': {
                'city': 'الإسكندرية',
            },
            'سينما سان جيوفاني': {
                'city': 'الإسكندرية',
            },
            'سينما المنشية': {
                'city': 'الإسكندرية',
            },
        }

        created_venues = 0
        skipped_venues = 0

        for name, venue_data in venues_data.items():
            # Check if venue already exists
            existing = CinemaVenue.objects.filter(name=name).first()
            
            if existing:
                self.stdout.write(self.style.WARNING(f'Venue already exists: {name}'))
                skipped_venues += 1
                continue

            # Create venue
            venue = CinemaVenue.objects.create(
                name=name,
                city=venue_data['city'],
            )
            
            created_venues += 1
            self.stdout.write(self.style.SUCCESS(f'Created venue: {name}'))

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_venues} cinema venues. '
                f'Skipped {skipped_venues} already existing.'
            )
        )
