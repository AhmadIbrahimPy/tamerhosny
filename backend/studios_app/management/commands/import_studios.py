import os
import requests
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from backend.studios_app.models import Studio


class Command(BaseCommand):
    help = 'Import Tamer Hosny production companies and studios with logos'

    def handle(self, *args, **kwargs):
        studios_data = [
            {
                'name': 'TH Production',
                'name_ar': 'تي إتش برودكشن',
                'entity_type': 'PRODUCTION_COMPANY',
                'description': 'شركة الإنتاج الخاصة بالفنان تامر حسني',
                'logo_url': None,  # No official logo found
            },
            {
                'name': 'Free Music Art Production',
                'name_ar': 'فري ميوزيك آرت برودكشن',
                'entity_type': 'RECORD_LABEL',
                'description': 'شركة تسجيلات موسيقية أسسها نصر محروس',
                'logo_url': None,  # Logo not available
            },
            {
                'name': 'Mazzika',
                'name_ar': 'مزيكا',
                'entity_type': 'RECORD_LABEL',
                'description': 'شركة تسجيلات موسيقية مصرية',
                'logo_url': 'https://upload.wikimedia.org/wikipedia/commons/c/cd/Mazzika_Logo.png',
            },
            {
                'name': 'Rotana',
                'name_ar': 'روتانا',
                'entity_type': 'RECORD_LABEL',
                'description': 'شركة تسجيلات وإنتاج موسيقي عربية',
                'logo_url': None,  # Will use Wikipedia SVG
            },
        ]
        
        created_count = 0
        updated_count = 0
        logo_added_count = 0
        
        for studio_data in studios_data:
            name = studio_data['name']
            existing_studio = Studio.objects.filter(name=name).first()
            
            # Download logo if URL provided
            logo_file = None
            if studio_data['logo_url']:
                try:
                    response = requests.get(studio_data['logo_url'], timeout=30)
                    if response.status_code == 200:
                        # Get file extension from URL
                        ext = '.png' if '.png' in studio_data['logo_url'] else '.svg'
                        logo_file = ContentFile(response.content)
                        logo_file.name = f'{name.replace(" ", "_").lower()}{ext}'
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'Failed to download logo for {name}: {e}'))
            
            if existing_studio:
                if logo_file and not existing_studio.logo:
                    existing_studio.logo = logo_file
                    existing_studio.save()
                    logo_added_count += 1
                    self.stdout.write(f'Updated with logo: {name}')
                else:
                    updated_count += 1
                    self.stdout.write(f'Updated: {name}')
            else:
                Studio.objects.create(
                    name=name,
                    entity_type=studio_data['entity_type'],
                    logo=logo_file,
                )
                created_count += 1
                if logo_file:
                    logo_added_count += 1
                self.stdout.write(f'Created: {name}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully imported {created_count} studios, updated {updated_count} studios, added {logo_added_count} logos'
            )
        )
        if logo_added_count < len(studios_data):
            self.stdout.write(
                self.style.WARNING(
                    'Note: Some logos could not be downloaded automatically. Add them manually through the admin panel.'
                )
            )
