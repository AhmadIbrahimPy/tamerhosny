from PIL import Image, ImageDraw, ImageFont
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from io import BytesIO
from backend.media_app.models import Media


class Command(BaseCommand):
    help = 'Create simple poster images for movies using PIL'

    def handle(self, *args, **options):
        # Get all movies
        movies = Media.objects.filter(media_type='MOVIE')
        
        updated_count = 0
        skipped_count = 0

        for movie in movies:
            if movie.poster_image:
                self.stdout.write(self.style.WARNING(f'Movie already has poster: {movie.title_ar}'))
                skipped_count += 1
                continue

            try:
                # Create a simple image with the movie title
                img = Image.new('RGB', (400, 600), color='#1a1a2e')
                draw = ImageDraw.Draw(img)
                
                # Try to use a default font, fallback to default if not available
                try:
                    font = ImageFont.truetype('/System/Library/Fonts/Arial.ttf', 24)
                except:
                    font = ImageFont.load_default()
                
                # Draw the movie title
                text = movie.title_ar
                if movie.title_en:
                    text = f"{movie.title_ar}\n{movie.title_en}"
                
                # Calculate text position (center)
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                x = (400 - text_width) / 2
                y = (600 - text_height) / 2
                
                draw.text((x, y), text, fill='white', font=font)
                
                # Save to BytesIO
                img_io = BytesIO()
                img.save(img_io, format='JPEG')
                img_io.seek(0)
                
                # Save to the movie's poster_image field
                file_name = f"{movie.slug}_poster.jpg"
                movie.poster_image.save(file_name, ContentFile(img_io.read()), save=True)
                movie.save()

                self.stdout.write(self.style.SUCCESS(f'Created poster for: {movie.title_ar}'))
                updated_count += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error creating poster for {movie.title_ar}: {str(e)}'))
                skipped_count += 1

        self.stdout.write(self.style.SUCCESS(f'\nSummary: Created {updated_count} posters, Skipped {skipped_count}'))
