import os
import requests
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.core.files.temp import NamedTemporaryFile
from backend.media_app.models import Media


class Command(BaseCommand):
    help = 'Import poster images for movies from URLs'

    def handle(self, *args, **options):
        # Dictionary of movie titles and their poster URLs
        # Using placeholder URLs since actual movie poster URLs are not easily accessible
        # These will need to be replaced with actual poster URLs when available
        movie_posters = {
            'ريستارت': 'https://via.placeholder.com/400x600/1a1a2e/ffffff?text=Restart',
            'تاج': 'https://via.placeholder.com/400x600/1a1a2e/ffffff?text=Taj',
            'بحبك': 'https://via.placeholder.com/400x600/1a1a2e/ffffff?text=Bahebak',
            'مش أنا': 'https://via.placeholder.com/400x600/1a1a2e/ffffff?text=Mosh+Ana',
            'الفلوس': 'https://via.placeholder.com/400x600/1a1a2e/ffffff?text=El+Folous',
            'البدلة': 'https://via.placeholder.com/400x600/1a1a2e/ffffff?text=El+Badla',
            'تصبح على خير': 'https://via.placeholder.com/400x600/1a1a2e/ffffff?text=Tesbah+Ala+Kheir',
            'أهواك': 'https://via.placeholder.com/400x600/1a1a2e/ffffff?text=Ahwak',
            'عمر وسلمى 3': 'https://via.placeholder.com/400x600/1a1a2e/ffffff?text=Omar+Salma+3',
            'نور عيني': 'https://via.placeholder.com/400x600/1a1a2e/ffffff?text=Nour+Einy',
            'عمر وسلمى 2': 'https://via.placeholder.com/400x600/1a1a2e/ffffff?text=Omar+Salma+2',
            'كابتن هيما': 'https://via.placeholder.com/400x600/1a1a2e/ffffff?text=Captain+Hema',
            'عمر وسلمى': 'https://via.placeholder.com/400x600/1a1a2e/ffffff?text=Omar+Salma',
            'سيد العاطفي': 'https://via.placeholder.com/400x600/1a1a2e/ffffff?text=Sayed+El+Atefi',
            'حالة حب': 'https://via.placeholder.com/400x600/1a1a2e/ffffff?text=Halat+Hob',
        }

        updated_count = 0
        skipped_count = 0

        for movie_title, poster_url in movie_posters.items():
            movie = Media.objects.filter(title_ar=movie_title).first()
            if not movie:
                self.stdout.write(self.style.WARNING(f'Movie not found: {movie_title}'))
                skipped_count += 1
                continue

            if movie.poster_image:
                self.stdout.write(self.style.WARNING(f'Movie already has poster: {movie_title}'))
                skipped_count += 1
                continue

            try:
                # Download the image
                response = requests.get(poster_url, stream=True)
                response.raise_for_status()

                # Save the image to a temporary file
                img_temp = NamedTemporaryFile(delete=True)
                img_temp.write(response.content)
                img_temp.flush()

                # Save the image to the movie's poster_image field
                file_name = os.path.basename(poster_url.split('?')[0])
                movie.poster_image.save(file_name, ContentFile(img_temp.read()), save=True)
                movie.save()

                self.stdout.write(self.style.SUCCESS(f'Updated poster for: {movie_title}'))
                updated_count += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error updating poster for {movie_title}: {str(e)}'))
                skipped_count += 1

        self.stdout.write(self.style.SUCCESS(f'\nSummary: Updated {updated_count} movies, Skipped {skipped_count}'))
