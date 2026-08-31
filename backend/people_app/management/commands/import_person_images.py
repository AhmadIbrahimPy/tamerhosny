import os
import requests
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.core.files.temp import NamedTemporaryFile
from backend.people_app.models import Person


class Command(BaseCommand):
    help = 'Import profile images for people from URLs'

    def handle(self, *args, **options):
        # Dictionary of person names and their image URLs
        person_images = {
            'تامر حسني': 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/86/Tamer_Hosny_2022.jpg/440px-Tamer_Hosny_2022.jpg',
            # Add more people and their image URLs here
        }

        updated_count = 0
        skipped_count = 0

        for person_name, image_url in person_images.items():
            person = Person.objects.filter(full_name_ar=person_name).first()
            if not person:
                self.stdout.write(self.style.WARNING(f'Person not found: {person_name}'))
                skipped_count += 1
                continue

            if person.profile_image:
                self.stdout.write(self.style.WARNING(f'Person already has image: {person_name}'))
                skipped_count += 1
                continue

            try:
                # Download the image
                response = requests.get(image_url, stream=True)
                response.raise_for_status()

                # Save the image to a temporary file
                img_temp = NamedTemporaryFile(delete=True)
                img_temp.write(response.content)
                img_temp.flush()

                # Save the image to the person's profile_image field
                file_name = os.path.basename(image_url.split('?')[0])
                person.profile_image.save(file_name, ContentFile(img_temp.read()), save=True)
                person.save()

                self.stdout.write(self.style.SUCCESS(f'Updated image for: {person_name}'))
                updated_count += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error updating image for {person_name}: {str(e)}'))
                skipped_count += 1

        self.stdout.write(self.style.SUCCESS(f'\nSummary: Updated {updated_count} people, Skipped {skipped_count}'))
