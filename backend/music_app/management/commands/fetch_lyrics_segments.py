from django.core.management.base import BaseCommand
from django.db import transaction
import requests
from bs4 import BeautifulSoup
import re
from decimal import Decimal

from backend.music_app.models import Song, SongLyricSegment


class Command(BaseCommand):
    help = 'Fetch song lyrics from internet and create timed segments'

    def add_arguments(self, parser):
        parser.add_argument(
            '--song-id',
            type=int,
            help='Specific song ID to fetch lyrics for',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Fetch lyrics for all songs without segments',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually saving',
        )

    def handle(self, *args, **kwargs):
        song_id = kwargs.get('song_id')
        fetch_all = kwargs.get('all')
        dry_run = kwargs.get('dry_run')

        if song_id:
            songs = Song.objects.filter(id=song_id)
        elif fetch_all:
            songs = Song.objects.filter(lyric_segments__isnull=True)
        else:
            self.stdout.write(self.style.ERROR('Please specify either --song-id or --all'))
            return

        for song in songs:
            self.stdout.write(f'\nProcessing: {song.title_ar} ({song.title_en})')
            
            # Try to fetch lyrics from multiple sources
            lyrics = self.fetch_lyrics_from_sources(song)
            
            if not lyrics:
                self.stdout.write(self.style.WARNING(f'No lyrics found for {song.title_ar}'))
                continue
            
            # Clean and parse lyrics
            if isinstance(lyrics, dict) and lyrics.get('lrc'):
                # LRC format has timing built-in
                segments = self.parse_lrc_format(lyrics['lrc'], song)
            elif isinstance(lyrics, dict) and lyrics.get('plain'):
                # Plain lyrics need timing calculation
                cleaned_lyrics = self.clean_lyrics(lyrics['plain'])
                if not cleaned_lyrics:
                    self.stdout.write(self.style.WARNING(f'Empty lyrics after cleaning for {song.title_ar}'))
                    continue
                segments = self.create_timed_segments(song, cleaned_lyrics)
            else:
                cleaned_lyrics = self.clean_lyrics(lyrics)
                if not cleaned_lyrics:
                    self.stdout.write(self.style.WARNING(f'Empty lyrics after cleaning for {song.title_ar}'))
                    continue
                segments = self.create_timed_segments(song, cleaned_lyrics)
            
            if dry_run:
                self.stdout.write(f'DRY RUN - Would create {len(segments)} segments for {song.title_ar}:')
                for seg in segments[:5]:  # Show first 5
                    self.stdout.write(f'  [{seg["start_seconds"]}s-{seg["end_seconds"]}s] {seg["segment_type"]}: {seg["text"][:50]}...')
                if len(segments) > 5:
                    self.stdout.write(f'  ... and {len(segments) - 5} more segments')
            else:
                # Save segments to database
                with transaction.atomic():
                    # Delete existing segments for this song
                    song.lyric_segments.all().delete()
                    
                    # Create new segments
                    SongLyricSegment.objects.bulk_create([
                        SongLyricSegment(
                            song=song,
                            start_seconds=seg['start_seconds'],
                            end_seconds=seg['end_seconds'],
                            segment_type=seg['segment_type'],
                            text=seg['text']
                        )
                        for seg in segments
                    ])
                
                self.stdout.write(self.style.SUCCESS(f'Created {len(segments)} segments for {song.title_ar}'))

    def fetch_lyrics_from_sources(self, song):
        """Try to fetch lyrics from multiple sources, prioritizing LRC format"""
        # External API fetching disabled - causing errors
        return None

    def fetch_lrc_format(self, song):
        """Try to fetch LRC format lyrics (with timing) from various sources"""
        # Search for LRC files on common lyrics sites
        search_terms = [
            f'{song.title_ar} lrc',
            f'{song.title_en if song.title_en else song.title_ar} lrc',
        ]
        
        for term in search_terms:
            try:
                # Try to find LRC from lyrics.wikia or similar
                url = f'https://lyrics.fandom.com/wiki/{term.replace(" ", "_")}'
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    # Look for LRC download links or embedded LRC content
                    lrc_link = soup.find('a', href=re.compile(r'\.lrc$'))
                    if lrc_link:
                        lrc_url = lrc_link['href']
                        lrc_response = requests.get(lrc_url, timeout=10)
                        if lrc_response.status_code == 200:
                            return {'lrc': lrc_response.text}
            except:
                continue
        
        return None

    def parse_lrc_format(self, lrc_text, song):
        """Parse LRC format lyrics with timing"""
        segments = []
        lines = lrc_text.split('\n')
        
        # LRC format: [mm:ss.xx] lyrics
        lrc_pattern = re.compile(r'\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)')
        
        for line in lines:
            match = lrc_pattern.match(line.strip())
            if match:
                minutes = int(match.group(1))
                seconds = int(match.group(2))
                centiseconds = int(match.group(3))
                text = match.group(4).strip()
                
                start_time = Decimal(str(minutes * 60 + seconds + centiseconds / 100))
                
                # Determine segment type
                if not text or len(text) < 2:
                    segment_type = SongLyricSegment.SegmentType.MUSIC
                else:
                    arabic_chars = len(re.findall(r'[\u0600-\u06FF]', text))
                    english_chars = len(re.findall(r'[a-zA-Z]', text))
                    total_chars = len(text)
                    
                    if total_chars > 0 and (arabic_chars + english_chars) / total_chars < 0.3:
                        segment_type = SongLyricSegment.SegmentType.MUSIC
                    else:
                        segment_type = SongLyricSegment.SegmentType.LYRICS
                
                segments.append({
                    'start_seconds': start_time,
                    'end_seconds': None,  # Will be set based on next segment
                    'segment_type': segment_type,
                    'text': text if segment_type == SongLyricSegment.SegmentType.LYRICS else ''
                })
        
        # Set end times based on next segment's start time
        for i in range(len(segments) - 1):
            segments[i]['end_seconds'] = segments[i + 1]['start_seconds']
        
        # Last segment ends at song duration or 30 seconds after start
        if segments:
            last_seg = segments[-1]
            if song.duration_seconds:
                last_seg['end_seconds'] = Decimal(str(song.duration_seconds))
            else:
                last_seg['end_seconds'] = last_seg['start_seconds'] + Decimal('30')
        
        return segments

    def fetch_from_melody4arab(self, song):
        """Fetch lyrics from melody4arab.com"""
        search_url = f'https://www.melody4arab.com/search.php?search={song.title_ar}'
        
        try:
            response = requests.get(search_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find song links
            song_links = soup.find_all('a', href=re.compile(r'/lyrics/'))
            
            for link in song_links:
                if song.title_ar.lower() in link.get_text().lower():
                    song_url = f"https://www.melody4arab.com{link['href']}"
                    lyrics_response = requests.get(song_url, timeout=10)
                    lyrics_soup = BeautifulSoup(lyrics_response.text, 'html.parser')
                    
                    # Find lyrics div
                    lyrics_div = lyrics_soup.find('div', class_='lyrics') or lyrics_soup.find('div', id='lyrics')
                    if lyrics_div:
                        return lyrics_div.get_text(strip=True)
        except Exception as e:
            self.stdout.write(f'Melody4arab error: {str(e)}')
        
        return None

    def fetch_from_arabiclyrics(self, song):
        """Fetch lyrics from arabiclyrics.net"""
        search_url = f'https://www.arabiclyrics.net/search?q={song.title_ar}'
        
        try:
            response = requests.get(search_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find song links
            song_links = soup.find_all('a', href=re.compile(r'/song/'))
            
            for link in song_links:
                if song.title_ar.lower() in link.get_text().lower():
                    song_url = f"https://www.arabiclyrics.net{link['href']}"
                    lyrics_response = requests.get(song_url, timeout=10)
                    lyrics_soup = BeautifulSoup(lyrics_response.text, 'html.parser')
                    
                    # Find lyrics div
                    lyrics_div = lyrics_soup.find('div', class_='lyrics-content') or lyrics_soup.find('div', class_='song-lyrics')
                    if lyrics_div:
                        return lyrics_div.get_text(strip=True)
        except Exception as e:
            self.stdout.write(f'Arabiclyrics error: {str(e)}')
        
        return None

    def fetch_from_elyrics(self, song):
        """Fetch lyrics from elyrics.net"""
        search_url = f'https://www.elyrics.net/search/{song.title_en if song.title_en else song.title_ar}'
        
        try:
            response = requests.get(search_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find song links
            song_links = soup.find_all('a', href=re.compile(r'/read/'))
            
            for link in song_links:
                song_title = link.get_text().lower()
                search_title = (song.title_en or song.title_ar).lower()
                if search_title in song_title or song_title in search_title:
                    song_url = f"https://www.elyrics.net{link['href']}"
                    lyrics_response = requests.get(song_url, timeout=10)
                    lyrics_soup = BeautifulSoup(lyrics_response.text, 'html.parser')
                    
                    # Find lyrics div
                    lyrics_div = lyrics_soup.find('div', class_='lyrics') or lyrics_soup.find('div', id='lyrics')
                    if lyrics_div:
                        return lyrics_div.get_text(strip=True)
        except Exception as e:
            self.stdout.write(f'ELyrics error: {str(e)}')
        
        return None

    def clean_lyrics(self, lyrics):
        """Clean and normalize lyrics text"""
        # Remove common non-lyric text
        patterns_to_remove = [
            r'Lyrics\s*[:\-]?\s*',
            r'\[.*?\]',  # Remove [Chorus], [Verse], etc.
            r'\(.*?\)',  # Remove parenthetical text
            r'www\.\w+\.com',
            r'Share\s+this\s+song',
            r'Print\s+these\s+lyrics',
            r'\d+\s*comments?',
        ]
        
        cleaned = lyrics
        for pattern in patterns_to_remove:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Split into lines and filter empty ones
        lines = [line.strip() for line in cleaned.split('\n')]
        lines = [line for line in lines if line and len(line) > 2]
        
        return lines

    def create_timed_segments(self, song, lyrics_lines):
        """Create timed segments from lyrics lines"""
        segments = []
        
        if not song.duration_seconds:
            self.stdout.write(self.style.WARNING(f'No duration for {song.title_ar}, using default 180s'))
            total_duration = Decimal('180')
        else:
            total_duration = Decimal(str(song.duration_seconds))
        
        # Calculate time per line
        num_lines = len(lyrics_lines)
        if num_lines == 0:
            return segments
        
        time_per_line = total_duration / num_lines
        
        current_time = Decimal('0')
        
        for i, line in enumerate(lyrics_lines):
            start_time = current_time
            end_time = current_time + time_per_line
            
            # Determine segment type
            # If line is mostly non-alphabetic, consider it music/silence
            arabic_chars = len(re.findall(r'[\u0600-\u06FF]', line))
            english_chars = len(re.findall(r'[a-zA-Z]', line))
            total_chars = len(line)
            
            if total_chars > 0 and (arabic_chars + english_chars) / total_chars < 0.3:
                # Mostly non-lyrical (music, sound effects, etc.)
                segment_type = SongLyricSegment.SegmentType.MUSIC
            else:
                segment_type = SongLyricSegment.SegmentType.LYRICS
            
            segments.append({
                'start_seconds': round(start_time, 2),
                'end_seconds': round(end_time, 2),
                'segment_type': segment_type,
                'text': line if segment_type == SongLyricSegment.SegmentType.LYRICS else ''
            })
            
            current_time = end_time
        
        return segments
