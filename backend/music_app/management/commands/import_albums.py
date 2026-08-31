import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand

from backend.music_app.models import Album


class Command(BaseCommand):
    help = 'Import Tamer Hosny albums from albumaty.com'

    def handle(self, *args, **kwargs):
        url = 'https://www.albumaty.com/singer/71.html'
        
        self.stdout.write(f'Fetching albums from {url}...')
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all album links in the albums section
            album_links = soup.find_all('a', href=re.compile(r'/album/\d+\.html'))
            
            albums_data = []
            for link in album_links:
                text = link.get_text(strip=True)
                self.stdout.write(f'Processing: {text}')
                # Extract album name and year
                # Format: "ألبوم اسم الألبوم    YEAR" or "ألبوم اسم الألبومYEAR"
                match = re.search(r'ألبوم\s+(.+?)(\s+\d{4})$', text)
                if not match:
                    # Try without space before year
                    match = re.search(r'ألبوم\s+(.+?)(\d{4})$', text)
                if match:
                    album_name = match.group(1).strip()
                    year_str = match.group(2).strip()
                    # Handle case like " 32012" -> extract 2012
                    year_match = re.search(r'(\d{4})', year_str)
                    if year_match:
                        year = int(year_match.group(1))
                        albums_data.append((album_name, year))
            
            # Remove duplicates
            albums_data = list(dict.fromkeys(albums_data))
            
            self.stdout.write(f'Found {len(albums_data)} unique albums')
            
            created_count = 0
            updated_count = 0
            
            for album_name, year in albums_data:
                # Generate English title (transliterate or use Arabic as fallback)
                title_en = self._transliterate_to_english(album_name)
                
                # Check if album already exists
                existing_album = Album.objects.filter(title_ar=album_name).first()
                
                if existing_album:
                    existing_album.release_date = datetime(year, 1, 1).date()
                    existing_album.save()
                    updated_count += 1
                    self.stdout.write(f'Updated: {album_name} ({year})')
                else:
                    Album.objects.create(
                        title_ar=album_name,
                        title_en=title_en,
                        release_date=datetime(year, 1, 1).date(),
                        visibility='PUBLISHED'
                    )
                    created_count += 1
                    self.stdout.write(f'Created: {album_name} ({year})')
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully imported {created_count} albums, updated {updated_count} albums'
                )
            )
            
        except requests.RequestException as e:
            self.stdout.write(self.style.ERROR(f'Failed to fetch data: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}'))
    
    def _transliterate_to_english(self, arabic_text):
        """Simple transliteration from Arabic to English for slug generation"""
        # This is a basic mapping - you may want to improve this
        arabic_to_english = {
            'ا': 'a', 'أ': 'a', 'إ': 'i', 'آ': 'aa',
            'ب': 'b', 'ت': 't', 'ث': 'th',
            'ج': 'j', 'ح': 'h', 'خ': 'kh',
            'د': 'd', 'ذ': 'dh', 'ر': 'r', 'ز': 'z',
            'س': 's', 'ش': 'sh', 'ص': 's', 'ض': 'd',
            'ط': 't', 'ظ': 'z', 'ع': 'a', 'غ': 'gh',
            'ف': 'f', 'ق': 'q', 'ك': 'k', 'ل': 'l',
            'م': 'm', 'ن': 'n', 'ه': 'h', 'و': 'w',
            'ي': 'y', 'ة': 'a', ' ': '-', 'ى': 'a'
        }
        
        english = ''
        for char in arabic_text:
            english += arabic_to_english.get(char, char)
        
        return english.lower()
