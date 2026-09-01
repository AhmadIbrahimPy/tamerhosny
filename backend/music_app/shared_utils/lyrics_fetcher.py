from django.db import transaction
from decimal import Decimal
import requests
from bs4 import BeautifulSoup
import re

from backend.music_app.models import Song, SongLyricSegment


def fetch_and_save_lyrics_for_song(song):
    """
    Fetch lyrics from internet and save as SongLyricSegment for a given song.
    Returns True if successful, False otherwise.
    """
    if not song:
        return False
    
    # Check if segments already exist
    if song.lyric_segments.exists():
        return True
    
    try:
        # Try to fetch lyrics from multiple sources
        lyrics = fetch_lyrics_from_sources(song)
        
        if not lyrics:
            return False
        
        # Parse and create segments
        segments = parse_lyrics_to_segments(song, lyrics)
        
        if not segments:
            return False
        
        # Save segments to database
        with transaction.atomic():
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
        
        return True
        
    except Exception as e:
        print(f"Error fetching lyrics for {song.title_ar}: {str(e)}")
        return False


def fetch_lyrics_from_sources(song):
    """Try to fetch lyrics from multiple sources"""
    # External API fetching disabled - causing errors
    return None


def parse_lyrics_to_segments(song, lyrics):
    """Parse lyrics (LRC or plain) into timed segments"""
    if isinstance(lyrics, dict) and lyrics.get('lrc'):
        return parse_lrc_format(lyrics['lrc'], song)
    elif isinstance(lyrics, dict) and lyrics.get('plain'):
        cleaned_lyrics = clean_lyrics(lyrics['plain'])
        if cleaned_lyrics:
            return create_timed_segments(song, cleaned_lyrics)
    else:
        cleaned_lyrics = clean_lyrics(lyrics)
        if cleaned_lyrics:
            return create_timed_segments(song, cleaned_lyrics)
    
    return []


def fetch_lrc_format(song):
    """Try to fetch LRC format lyrics (with timing) from various sources"""
    search_terms = [
        f'{song.title_ar} lrc',
        f'{song.title_en if song.title_en else song.title_ar} lrc',
    ]
    
    for term in search_terms:
        try:
            url = f'https://lyrics.fandom.com/wiki/{term.replace(" ", "_")}'
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                lrc_link = soup.find('a', href=re.compile(r'\.lrc$'))
                if lrc_link:
                    lrc_url = lrc_link['href']
                    lrc_response = requests.get(lrc_url, timeout=10)
                    if lrc_response.status_code == 200:
                        return {'lrc': lrc_response.text}
        except:
            continue
    
    return None


def parse_lrc_format(lrc_text, song):
    """Parse LRC format lyrics with timing"""
    segments = []
    lines = lrc_text.split('\n')
    
    lrc_pattern = re.compile(r'\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)')
    
    for line in lines:
        match = lrc_pattern.match(line.strip())
        if match:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            centiseconds = int(match.group(3))
            text = match.group(4).strip()
            
            start_time = Decimal(str(minutes * 60 + seconds + centiseconds / 100))
            
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
                'end_seconds': None,
                'segment_type': segment_type,
                'text': text if segment_type == SongLyricSegment.SegmentType.LYRICS else ''
            })
    
    for i in range(len(segments) - 1):
        segments[i]['end_seconds'] = segments[i + 1]['start_seconds']
    
    if segments:
        last_seg = segments[-1]
        if song.duration_seconds:
            last_seg['end_seconds'] = Decimal(str(song.duration_seconds))
        else:
            last_seg['end_seconds'] = last_seg['start_seconds'] + Decimal('30')
    
    return segments


def fetch_from_melody4arab(song):
    """Fetch lyrics from melody4arab.com"""
    search_url = f'https://www.melody4arab.com/search.php?search={song.title_ar}'
    
    try:
        response = requests.get(search_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        song_links = soup.find_all('a', href=re.compile(r'/lyrics/'))
        
        for link in song_links:
            if song.title_ar.lower() in link.get_text().lower():
                song_url = f"https://www.melody4arab.com{link['href']}"
                lyrics_response = requests.get(song_url, timeout=10)
                lyrics_soup = BeautifulSoup(lyrics_response.text, 'html.parser')
                
                lyrics_div = lyrics_soup.find('div', class_='lyrics') or lyrics_soup.find('div', id='lyrics')
                if lyrics_div:
                    return lyrics_div.get_text(strip=True)
    except Exception as e:
        print(f'Melody4arab error: {str(e)}')
    
    return None


def fetch_from_arabiclyrics(song):
    """Fetch lyrics from arabiclyrics.net"""
    search_url = f'https://www.arabiclyrics.net/search?q={song.title_ar}'
    
    try:
        response = requests.get(search_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        song_links = soup.find_all('a', href=re.compile(r'/song/'))
        
        for link in song_links:
            if song.title_ar.lower() in link.get_text().lower():
                song_url = f"https://www.arabiclyrics.net{link['href']}"
                lyrics_response = requests.get(song_url, timeout=10)
                lyrics_soup = BeautifulSoup(lyrics_response.text, 'html.parser')
                
                lyrics_div = lyrics_soup.find('div', class_='lyrics-content') or lyrics_soup.find('div', class_='song-lyrics')
                if lyrics_div:
                    return lyrics_div.get_text(strip=True)
    except Exception as e:
        print(f'Arabiclyrics error: {str(e)}')
    
    return None


def fetch_from_elyrics(song):
    """Fetch lyrics from elyrics.net"""
    search_url = f'https://www.elyrics.net/search/{song.title_en if song.title_en else song.title_ar}'
    
    try:
        response = requests.get(search_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        song_links = soup.find_all('a', href=re.compile(r'/read/'))
        
        for link in song_links:
            song_title = link.get_text().lower()
            search_title = (song.title_en or song.title_ar).lower()
            if search_title in song_title or song_title in search_title:
                song_url = f"https://www.elyrics.net{link['href']}"
                lyrics_response = requests.get(song_url, timeout=10)
                lyrics_soup = BeautifulSoup(lyrics_response.text, 'html.parser')
                
                lyrics_div = lyrics_soup.find('div', class_='lyrics') or lyrics_soup.find('div', id='lyrics')
                if lyrics_div:
                    return lyrics_div.get_text(strip=True)
    except Exception as e:
        print(f'ELyrics error: {str(e)}')
    
    return None


def clean_lyrics(lyrics):
    """Clean and normalize lyrics text"""
    patterns_to_remove = [
        r'Lyrics\s*[:\-]?\s*',
        r'\[.*?\]',
        r'\(.*?\)',
        r'www\.\w+\.com',
        r'Share\s+this\s+song',
        r'Print\s+these\s+lyrics',
        r'\d+\s*comments?',
    ]
    
    cleaned = lyrics
    for pattern in patterns_to_remove:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    
    lines = [line.strip() for line in cleaned.split('\n')]
    lines = [line for line in lines if line and len(line) > 2]
    
    return lines


def create_timed_segments(song, lyrics_lines):
    """Create timed segments from lyrics lines"""
    segments = []
    
    if not song.duration_seconds:
        total_duration = Decimal('180')
    else:
        total_duration = Decimal(str(song.duration_seconds))
    
    num_lines = len(lyrics_lines)
    if num_lines == 0:
        return segments
    
    time_per_line = total_duration / num_lines
    
    current_time = Decimal('0')
    
    for line in lyrics_lines:
        start_time = current_time
        end_time = current_time + time_per_line
        
        arabic_chars = len(re.findall(r'[\u0600-\u06FF]', line))
        english_chars = len(re.findall(r'[a-zA-Z]', line))
        total_chars = len(line)
        
        if total_chars > 0 and (arabic_chars + english_chars) / total_chars < 0.3:
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
