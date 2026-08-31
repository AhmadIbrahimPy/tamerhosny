from django.core.management.base import BaseCommand

from backend.music_app.models import Album
from backend.studios_app.models import Studio


class Command(BaseCommand):
    help = 'Link Tamer Hosny albums to their production companies'

    def handle(self, *args, **kwargs):
        # Album to studio mapping
        album_studio_mapping = {
            # Free Music (فري ميوزيك - نصر محروس)
            'فرى ميكس 3': 'Free Music Art Production',
            'حب': 'Free Music Art Production',
            'عينيه بتحبك': 'Free Music Art Production',
            'يا بنت الإيه': 'Free Music Art Production',
            'الجنه فى بيوتنا': 'Free Music Art Production',
            'قرب كمان': 'Free Music Art Production',
            'بحبك انت': 'Free Music Art Production',
            
            # Mazzika (عالم الفن / مزيكا - محسن جابر)
            'هاعيش حياتى': 'Mazzika',
            'اخترت صح': 'Mazzika',
            'اللى جاى احلى': 'Mazzika',
            'Smile': 'Mazzika',
            'اغانى فيلم عمر وسلمى 3': 'Mazzika',
            
            # Rotana (روتانا)
            '180 درجة': 'Rotana',
            'عمرى ابتدا': 'Rotana',
            
            # TH Production (شركة تامر حسني للإنتاج)
            'عيش بشوقك': 'TH Production',
            'خليك فولاذي': 'TH Production',
            'عشأنجي': 'TH Production',
            'بحبك': 'TH Production',
            'هرمون السعاده': 'TH Production',
            'لينا معاد': 'TH Production',
            'مش هتكرر': 'TH Production',
        }
        
        updated_count = 0
        not_found_count = 0
        
        for album_name, studio_name in album_studio_mapping.items():
            try:
                album = Album.objects.get(title_ar=album_name)
                studio = Studio.objects.get(name=studio_name)
                
                album.record_label = studio
                album.save()
                
                updated_count += 1
                self.stdout.write(f'Linked: {album_name} -> {studio_name}')
                
            except Album.DoesNotExist:
                not_found_count += 1
                self.stdout.write(self.style.WARNING(f'Album not found: {album_name}'))
            except Studio.DoesNotExist:
                not_found_count += 1
                self.stdout.write(self.style.WARNING(f'Studio not found: {studio_name}'))
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully linked {updated_count} albums to studios'
            )
        )
        
        if not_found_count > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'Could not link {not_found_count} albums (not found)'
                )
            )
