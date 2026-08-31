from PIL import Image, ImageDraw, ImageFont
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from io import BytesIO
from backend.people_app.models import Person


class Command(BaseCommand):
    help = 'Create simple profile images for people using PIL'

    def handle(self, *args, **options):
        # Get all people without images (either null or empty)
        people = Person.objects.filter(profile_image__isnull=True) | Person.objects.filter(profile_image='')
        
        updated_count = 0
        skipped_count = 0

        for person in people:
            try:
                # Create a simple image with the person's name
                img = Image.new('RGB', (300, 300), color='#2d3748')
                draw = ImageDraw.Draw(img)
                
                # Try to use a default font, fallback to default if not available
                try:
                    font = ImageFont.truetype('/System/Library/Fonts/Arial.ttf', 20)
                except:
                    font = ImageFont.load_default()
                
                # Draw the person's name
                text = person.full_name_ar
                if person.full_name_en:
                    text = f"{person.full_name_ar}\n{person.full_name_en}"
                
                # Calculate text position (center)
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                x = (300 - text_width) / 2
                y = (300 - text_height) / 2
                
                draw.text((x, y), text, fill='white', font=font)
                
                # Save to BytesIO
                img_io = BytesIO()
                img.save(img_io, format='JPEG')
                img_io.seek(0)
                
                # Save to the person's profile_image field
                file_name = f"{person.slug}_profile.jpg"
                person.profile_image.save(file_name, ContentFile(img_io.read()), save=True)
                person.save()

                self.stdout.write(self.style.SUCCESS(f'Created profile image for: {person.full_name_ar}'))
                updated_count += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error creating profile image for {person.full_name_ar}: {str(e)}'))
                skipped_count += 1

        self.stdout.write(self.style.SUCCESS(f'\nSummary: Created {updated_count} profile images, Skipped {skipped_count}'))
