import json
import random
import re
import unicodedata
from datetime import datetime, timedelta
from difflib import SequenceMatcher

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.db import models
from django.db.models import F, Q, Sum
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import get_language, gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from backend.ads_app.models import Advertisement
from backend.ai_remix_app.models import RemixProject, RemixSource, AudioSource
from backend.main_app.models import Like, Playlist, PlaylistItem, SongSimilarity, UserGameProfile, UserSongPlay, CurrentSongListener, VoiceAssistantLog, VoiceKnownPhrase
from backend.main_app.shared_utils.credits import dedupe_credits
from backend.main_app.shared_utils.llm_providers import ask_json
from backend.main_app.shared_utils.voice_shared import VOICE_NAV_PAGES, VOICE_VALID_INTENTS
from backend.main_app.shared_utils.gamification import (
    POINTS_GUESS_LOSS, POINTS_LIKE, award_points, get_rank_and_trend, unlocked_badges,
)
from backend.main_app.templatetags.bilingual import localized_field
from backend.concerts_app.models import Concert
from backend.media_app.models import Media
from backend.music_app.models import Album, DailyGuessAttempt, DailyGuessChallenge, Song, SongCredit, SingWithTamerProject
from backend.people_app.models import Person

PAGE_SIZE = 35


def _paginate(request, queryset):
    return Paginator(queryset, PAGE_SIZE).get_page(request.GET.get('page'))


def _ads_for(placement):
    """Every active ad eligible for a given public page (targeted at this
    placement specifically, or set to show everywhere).
    """
    return (
        Advertisement.objects.filter(is_active=True)
        .filter(Q(show_on_all_pages=True) | Q(placements__contains=[placement]))
        .order_by('?')
    )


def _ad_for(placement):
    """A single banner ad for pages that only show one at a time."""
    return _ads_for(placement).first()


def _ad_slots(placement):
    """Two ad banners for pages that show one near the top and one near the
    bottom — a different ad in each slot when more than one is eligible,
    otherwise the same ad repeated.
    """
    ads = list(_ads_for(placement)[:2])
    if not ads:
        return None, None
    top = ads[0]
    bottom = ads[1] if len(ads) > 1 else ads[0]
    return top, bottom


def robots_txt(request):
    lines = [
        'User-agent: *',
        'Allow: /',
        f'Disallow: /{settings.ADMIN_URL_PATH}/',
        f'Disallow: /{settings.DASHBOARD_URL_PATH}/',
        f'Sitemap: {request.build_absolute_uri("/sitemap.xml")}',
    ]
    return HttpResponse('\n'.join(lines), content_type='text/plain')


def home(request):
    songs = Song.visible_queryset(Song.objects.select_related('album'))[:7]
    sing_with_tamer_songs = Song.visible_queryset(
        Song.objects.select_related('album')
        .exclude(audio_file='')
        .filter(lyric_segments__isnull=False)
        .distinct()
    )[:10]
    movies = Media.visible_queryset(Media.objects.filter(media_type=Media.MediaType.MOVIE))[:7]
    series = Media.visible_queryset(Media.objects.filter(media_type=Media.MediaType.TV_SERIES))[:7]
    commercials = Media.visible_queryset(Media.objects.filter(media_type=Media.MediaType.COMMERCIAL))[:7]
    albums = Album.visible_queryset(Album.objects.all())[:7]
    concerts = Concert.visible_queryset(Concert.objects.all())[:4]
    people = Person.objects.all()[:8]
    home_ads = list(_ads_for(Advertisement.Placement.HOME)[:8])
    guess_played_today = request.user.is_authenticated and DailyGuessAttempt.objects.filter(
        user=request.user, challenge__date=timezone.localdate(),
    ).exists()
    return render(request, 'website/pages/home.html', {
        'guess_played_today': guess_played_today,
        'songs': songs,
        'sing_with_tamer_songs': sing_with_tamer_songs,
        'movies': movies,
        'series': series,
        'commercials': commercials,
        'albums': albums,
        'concerts': concerts,
        'people': people,
        'home_ads': home_ads,
        'mid_ad': home_ads[1] if len(home_ads) > 1 else (home_ads[0] if home_ads else None),
        'bottom_ad': home_ads[-1] if home_ads else None,
    })


def player_page(request):
    """Player page with song details and tabs."""
    return render(request, 'website/pages/player/index.html')


def tamer_bio(request):
    """A designed, animated biography page about Tamer Hosny."""
    tamer = Person.objects.filter(slug='tamer-hosny').first()
    stats = [
        {'value': '25+', 'label_ar': 'سنة من المشوار الفني', 'label_en': 'Years in the industry'},
        {'value': '30+', 'label_ar': 'ألبوم غنائي', 'label_en': 'Music albums'},
        {'value': '25+', 'label_ar': 'فيلم سينمائي', 'label_en': 'Feature films'},
        {'value': '100+', 'label_ar': 'أغنية منفردة وتعاونات', 'label_en': 'Singles & collaborations'},
    ]
    timeline = [
        {
            'year': '1977',
            'title_ar': 'البداية', 'title_en': 'The Beginning',
            'text_ar': 'وُلد تامر حسني في مدينة المنصورة، وبدأ شغفه بالموسيقى والتلحين منذ الطفولة.',
            'text_en': 'Tamer Hosny was born in Mansoura, Egypt, and his passion for music and composing began in early childhood.',
        },
        {
            'year': '1990',
            'title_ar': 'أول خطوة', 'title_en': 'First Steps',
            'text_ar': 'دخل عالم الغناء والتلحين وهو لا يزال في سن مبكرة، ولحّن أغاني لفنانين كبار قبل أن يطرح ألبومه الخاص.',
            'text_en': 'He entered the music scene at a young age, composing for established artists before releasing his own debut work.',
        },
        {
            'year': '2000',
            'title_ar': 'الانطلاقة', 'title_en': 'Breakthrough',
            'text_ar': 'حقق نجاحاً جماهيرياً واسعاً بألبوماته المتتالية وأغانيه التي سيطرت على الشارع العربي، ولُقّب بـ"نجم جيله".',
            'text_en': 'A string of hit albums and chart-topping singles made him one of the most prominent voices of his generation.',
        },
        {
            'year': '2005 - 2015',
            'title_ar': 'التمثيل والسينما', 'title_en': 'Acting & Cinema',
            'text_ar': 'خاض تجربة التمثيل السينمائي بنجاح كبير عبر سلسلة أفلام حققت إيرادات مرتفعة وحضوراً جماهيرياً واسعاً في مصر والعالم العربي.',
            'text_en': 'He built a highly successful film career, starring in a series of box-office hits across Egypt and the Arab world.',
        },
        {
            'year': '2010',
            'title_ar': 'انتشار عالمي', 'title_en': 'Going Global',
            'text_ar': 'قدّم تعاونات غنائية عالمية وشارك في حفلات دولية، ووصل صوته إلى جمهور أوسع خارج المنطقة العربية.',
            'text_en': 'International collaborations and global performances carried his sound to audiences far beyond the Arab world.',
        },
        {
            'year': 'اليوم', 'year_en': 'Today',
            'title_ar': 'مسيرة مستمرة', 'title_en': 'An Ongoing Journey',
            'text_ar': 'ما زال تامر حسني حاضراً بقوة في الساحة الفنية، بين الغناء والتلحين والتمثيل، محتفظاً بمكانته كأحد أهم نجوم الوطن العربي.',
            'text_en': 'Tamer Hosny remains a driving force across music, composing and film — one of the biggest names in the Arab world.',
        },
    ]
    return render(request, 'website/pages/bio.html', {'tamer': tamer, 'stats': stats, 'timeline': timeline})


@csrf_exempt
def song_player_data(request):
    """API endpoint to get song data for player page.

    `song_id` is optional: without one (e.g. landing on /player/ with no
    song in context), a random playable song is picked to seed the queue.

    `random=1` forces a random queue even when the song has an album -
    used when playback wasn't started from that album's own page, so
    next/prev elsewhere on the site don't just wander through its album.
    """
    try:
        song_id = request.POST.get('song_id') if request.method == 'POST' else request.GET.get('song_id')
        current_song_id = request.POST.get('current_song_id') if request.method == 'POST' else request.GET.get('current_song_id')
        force_random = (request.POST.get('random') if request.method == 'POST' else request.GET.get('random')) == '1'
        played_ids_param = request.POST.get('played_ids') if request.method == 'POST' else request.GET.get('played_ids')
        played_ids = [int(pk) for pk in played_ids_param.split(',') if pk.strip().isdigit()] if played_ids_param else []

        playable_songs = Song.objects.select_related('album').exclude(audio_file='')
        # User-submitted "Sing with Tamer" duets live as Song rows too
        # (is_duet=True) - fine to open directly, but they shouldn't turn
        # up as random catalog suggestions or seed a fresh queue.
        catalog_songs = Song.visible_queryset(playable_songs).filter(is_duet=False)

        if song_id:
            song = playable_songs.get(pk=song_id)
        else:
            song = catalog_songs.order_by('?').first()
            if not song:
                return JsonResponse({'error': 'No playable songs available'}, status=404)

        # Build the playback queue: same-album tracks when there is an
        # album (unless a random queue was explicitly requested),
        # otherwise a random playlist - always including the current
        # song itself so the player can locate it for next/prev.
        if song.album_id and not force_random:
            album_songs = list(
                catalog_songs.filter(album_id=song.album_id).order_by('title_ar')
            )
            if song not in album_songs:
                album_songs = [song] + album_songs
        else:
            remaining_catalog = catalog_songs.exclude(pk=song.pk)
            # Prefer something this session hasn't heard yet - only fall
            # back to allowing a repeat once that pool is actually empty.
            unheard = remaining_catalog.exclude(pk__in=played_ids) if played_ids else remaining_catalog
            random_songs = list((unheard if unheard.exists() else remaining_catalog).order_by('?')[:19])
            album_songs = [song] + random_songs
        # Get credits
        all_credits = list(song.credits.select_related('person').all())
        vocal_roles = (SongCredit.Role.SINGER, SongCredit.Role.FEATURED_ARTIST)
        singers = [credit for credit in all_credits if credit.role in vocal_roles]
        crew_credits = [credit for credit in all_credits if credit.role not in vocal_roles]

        song_ct = ContentType.objects.get_for_model(Song)

        data = {
            'title': localized_field(song, 'title'),
            'title_en': song.title_en,
            'slug': song.slug,
            'artist': ', '.join([localized_field(credit.person, 'full_name') for credit in singers]),
            'artistSlugs': [credit.person.slug for credit in singers],
            'album': localized_field(song.album, 'title') if song.album else '',
            'albumSlug': song.album.slug if song.album else '',
            'image': song.cover_image.url if song.cover_image else (song.album.cover_image.url if song.album and song.album.cover_image else ''),
            'songId': song.pk,
            'url': song.audio_file.url if song.audio_file else '',
            'currentSongId': int(current_song_id) if current_song_id else song.pk,
            'playCount': song.play_count,
            'likeCount': Like.objects.filter(content_type=song_ct, object_id=song.pk).count(),
            'listenerCount': CurrentSongListener.objects.filter(song_id=song.pk).count(),
            'otherSongs': [
                {
                    'title': localized_field(s, 'title'),
                    'image': s.cover_image.url if s.cover_image else (s.album.cover_image.url if s.album and s.album.cover_image else ''),
                    'link': f'/songs/{s.slug}/',
                    'duration': f"{s.duration_seconds // 60}:{s.duration_seconds % 60:02d}" if s.duration_seconds else '',
                    'songId': s.pk,
                    'url': s.audio_file.url if s.audio_file else '',
                    'artist': ', '.join([localized_field(credit.person, 'full_name') for credit in s.credits.select_related('person').all() if credit.role in vocal_roles]),
                    'album': localized_field(s.album, 'title') if s.album else ''
                }
                for s in album_songs
            ],
            'credits': [
                {
                    'personName': localized_field(credit.person, 'full_name'),
                    'personSlug': credit.person.slug,
                    'personImage': credit.person.profile_image.url if credit.person.profile_image else '',
                    'role': credit.get_role_display()
                }
                for credit in crew_credits
            ],
            'platforms': []
        }

        return JsonResponse(data)

    except Song.DoesNotExist:
        return JsonResponse({'error': 'Song not found'}, status=404)
    except Exception as e:
        import traceback
        print(f"Error in song_player_data: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return JsonResponse({'error': str(e)}, status=500)


_ARABIC_DIACRITICS_RE = re.compile(r'[ؐ-ًؚ-ْٰۖ-ۭ]')
_ARABIC_NORMALIZE_MAP = str.maketrans({
    'أ': 'ا', 'إ': 'ا', 'آ': 'ا', 'ٱ': 'ا',
    'ى': 'ي', 'ئ': 'ي',
    'ة': 'ه',
    'ؤ': 'و',
    'ـ': '',  # tatweel
    # Egyptian dialect pronounces ث like ت (not the formal "th") - a
    # speech engine transcribing "تاني" (again) routinely picks the
    # formal spelling "ثاني" instead, which then never matched a lyric
    # actually spelled with ت (e.g. "ما تخافش تاني من الحياة" heard back
    # as "...ثاني...").
    'ث': 'ت',
})


def _normalize_arabic(text):
    """Folds spelling variants a speech-to-text engine routinely picks
    between for the exact same spoken word - alef forms (أ/إ/آ), ya vs
    alef maqsura (ي/ى), ta marbuta vs ha (ة/ه), tashkeel - down to one
    canonical form, so a transcript like "اتحامي فيه" still matches a
    catalog title spelled "اتحامى فيا".
    """
    if not text:
        return ''
    text = unicodedata.normalize('NFKC', text)
    text = _ARABIC_DIACRITICS_RE.sub('', text)
    text = text.translate(_ARABIC_NORMALIZE_MAP)
    return re.sub(r'\s+', ' ', text).strip().lower()


def _title_match_score(query_norm, title_norm):
    if not title_norm or not query_norm:
        return 0.0
    if query_norm in title_norm or title_norm in query_norm:
        return 1.0
    return SequenceMatcher(None, query_norm, title_norm).ratio()


# How closely a live transcript has to match a previously-learned phrase
# (or one of its AI-generated paraphrases) before voice_intent() trusts
# it over calling the LLM fresh - stricter than song-title search's own
# threshold, since this one drives which action actually executes.
_KNOWN_PHRASE_MATCH_THRESHOLD = 0.75


def _find_known_phrase(text):
    """Fuzzy-matches `text` against VoiceKnownPhrase.original_transcript
    and every stored paraphrase (see that model's docstring) - the most
    recent 500 rows only, a pragmatic cap rather than a real limit on
    how many can ever be learned. Returns the best-matching row, or None
    if nothing clears the threshold.
    """
    text_norm = _normalize_arabic(text)
    text_lower = text.lower()
    best = None
    best_score = 0.0

    for phrase in VoiceKnownPhrase.objects.all()[:500]:
        for candidate in [phrase.original_transcript, *phrase.paraphrases]:
            score = _title_match_score(text_norm, _normalize_arabic(candidate))
            if score < 1.0:
                # Also try a plain-lowercase compare, in case the
                # transcript or a stored paraphrase came through in
                # Latin script (an English command/paraphrase).
                candidate_lower = candidate.lower()
                latin_score = 1.0 if text_lower in candidate_lower or candidate_lower in text_lower \
                    else SequenceMatcher(None, text_lower, candidate_lower).ratio()
                score = max(score, latin_score)
            if score > best_score:
                best_score = score
                best = phrase

    return best if best_score >= _KNOWN_PHRASE_MATCH_THRESHOLD else None


def voice_search_songs(request):
    """Backs the site-wide voice assistant ("TH" wake word).

    `q` matches song titles (for "شغل أغنية X"); `mood` matches
    Song.Mood (for "شغلي حاجة حزينة"/"روقان"/etc.); `lyrics` matches
    song lyrics (for "كلمات فيها X"/"غنية بتيقول X"); `album` matches an
    album by name (for "شغل أغنية من ألبوم X") and picks a random track
    from it; `year` picks a random song released that year (for "شغل
    حاجة 2010"), falling back to the closest year with any songs if
    that exact year has none; `era` is "OLD" or "RECENT" for a vague
    "شغل حاجة قديمة"/"شغل حاجة جديدة" with no specific year, picking
    from the oldest/newest quarter of the catalog. At least one of
    these is required. Results come back in the same per-song shape the
    player page's `otherSongs` queue items use, so the frontend can hand
    one straight to `playAudio()`/queue it without a second round trip.
    """
    query = (request.GET.get('q') or '').strip()
    mood = (request.GET.get('mood') or '').strip().upper()
    lyrics_query = (request.GET.get('lyrics') or '').strip()
    album_query = (request.GET.get('album') or '').strip()
    year_param = (request.GET.get('year') or '').strip()
    era_param = (request.GET.get('era') or '').strip().upper()
    try:
        limit = min(int(request.GET.get('limit', 10)), 20)
    except ValueError:
        limit = 10

    if not any([query, mood, lyrics_query, album_query, year_param, era_param]):
        return JsonResponse({'error': 'q, mood, lyrics, album, year, or era is required'}, status=400)

    playable_songs = Song.objects.select_related('album').exclude(audio_file='')
    queryset = Song.visible_queryset(playable_songs).filter(is_duet=False)

    if mood:
        if mood not in Song.Mood.values:
            return JsonResponse({'error': 'Unknown mood'}, status=400)
        queryset = queryset.filter(mood=mood)

    if query:
        # A plain DB icontains only catches an exact substring - a voice
        # transcript almost never spells Arabic exactly like the catalog
        # (different alef/ya/ta-marbuta forms, missing tashkeel, or just
        # a mis-heard letter), so rank every candidate by normalized
        # fuzzy similarity instead of filtering on an exact match.
        query_norm = _normalize_arabic(query)
        query_lower = query.lower()
        scored = []
        for s in queryset:
            score = _title_match_score(query_norm, _normalize_arabic(s.title_ar))
            if s.title_en:
                title_en_lower = s.title_en.lower()
                en_score = 1.0 if query_lower in title_en_lower or title_en_lower in query_lower \
                    else SequenceMatcher(None, query_lower, title_en_lower).ratio()
                score = max(score, en_score)
            if score >= 0.45:
                scored.append((score, s))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        songs = [s for _, s in scored[:limit]]
    elif lyrics_query:
        # Search in lyrics - the song's full lyrics text first (a plain
        # substring check there, not the fuzzy ratio used below:
        # SequenceMatcher's ratio is normalized by *combined* length, so
        # a short phrase against a whole song's lyrics scores low even
        # when it's an exact line from it), falling back to the per-line
        # LYRICS segments only for songs that don't have the full text
        # filled in yet either way. Full lyrics text comes from either
        # Song.lyrics or a FULL_SONG lyric_segment - two ways to enter
        # the same thing (see Song.full_lyrics_text) - so a song only
        # ever needs one of them to skip the slower per-segment fallback.
        # Each pass is scoped at the DB level to just the rows that
        # actually have something to check, instead of pulling and
        # looping the whole catalog through Python twice.
        from backend.music_app.models import SongLyricSegment

        lyrics_norm = _normalize_arabic(lyrics_query)
        lyrics_lower = lyrics_query.lower()
        scored = []

        has_full_lyrics = queryset.filter(
            Q(lyrics__gt='') | Q(lyric_segments__segment_type=SongLyricSegment.SegmentType.FULL_SONG),
        ).distinct()
        for s in has_full_lyrics:
            full_text = s.full_lyrics_text
            if not full_text:
                continue
            full_norm = _normalize_arabic(full_text)
            full_lower = full_text.lower()
            if lyrics_norm in full_norm or lyrics_lower in full_lower:
                scored.append((1.0, s))

        # A song with its full lyrics filled in (either way) already got
        # its shot above - only the ones missing both need the slower
        # per-segment fallback.
        missing_full_lyrics = queryset.filter(
            lyrics='', lyric_segments__segment_type='LYRICS',
        ).exclude(pk__in=has_full_lyrics.values_list('pk', flat=True)).distinct()
        for s in missing_full_lyrics:
            lyrics_score = 0.0
            for segment in s.lyric_segments.filter(segment_type='LYRICS'):
                if segment.text:
                    segment_norm = _normalize_arabic(segment.text)
                    segment_lower = segment.text.lower()

                    # Check for exact or partial match in normalized text
                    if lyrics_norm in segment_norm or segment_norm in lyrics_norm:
                        lyrics_score = max(lyrics_score, 1.0)
                    else:
                        lyrics_score = max(lyrics_score, SequenceMatcher(None, lyrics_norm, segment_norm).ratio())

                    # Also check lowercase for English lyrics
                    if lyrics_lower in segment_lower or segment_lower in lyrics_lower:
                        lyrics_score = max(lyrics_score, 1.0)

            if lyrics_score >= 0.5:
                scored.append((lyrics_score, s))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        songs = [s for _, s in scored[:limit]]
    elif album_query:
        album_norm = _normalize_arabic(album_query)
        album_lower = album_query.lower()
        best_album = None
        best_album_score = 0.0
        for a in Album.objects.all():
            score = _title_match_score(album_norm, _normalize_arabic(a.title_ar))
            if a.title_en:
                title_en_lower = a.title_en.lower()
                en_score = 1.0 if album_lower in title_en_lower or title_en_lower in album_lower \
                    else SequenceMatcher(None, album_lower, title_en_lower).ratio()
                score = max(score, en_score)
            if score > best_album_score:
                best_album_score = score
                best_album = a
        songs = list(queryset.filter(album=best_album).order_by('?')[:limit]) if best_album_score >= 0.45 else []
    elif year_param.isdigit():
        year = int(year_param)
        songs_with_year = queryset.exclude(release_year__isnull=True)
        songs = list(songs_with_year.filter(release_year=year).order_by('?')[:limit])
        if not songs:
            # Nothing released exactly that year - the closest year that
            # actually has songs reads better than an empty result for a
            # vague "شغل حاجة 2010"-style request.
            available_years = sorted(set(songs_with_year.values_list('release_year', flat=True)))
            if available_years:
                closest_year = min(available_years, key=lambda y: abs(y - year))
                songs = list(songs_with_year.filter(release_year=closest_year).order_by('?')[:limit])
    elif era_param in ('OLD', 'RECENT'):
        songs_with_year = queryset.exclude(release_year__isnull=True)
        available_years = sorted(set(songs_with_year.values_list('release_year', flat=True)))
        if available_years:
            quarter = max(1, len(available_years) // 4)
            era_years = available_years[:quarter] if era_param == 'OLD' else available_years[-quarter:]
            songs = list(songs_with_year.filter(release_year__in=era_years).order_by('?')[:limit])
        else:
            songs = []
    else:
        songs = list(queryset.order_by('?')[:limit])

    vocal_roles = (SongCredit.Role.SINGER, SongCredit.Role.FEATURED_ARTIST)
    results = [
        {
            'title': localized_field(s, 'title'),
            'image': s.cover_image.url if s.cover_image else (s.album.cover_image.url if s.album and s.album.cover_image else ''),
            'link': f'/songs/{s.slug}/',
            'duration': f"{s.duration_seconds // 60}:{s.duration_seconds % 60:02d}" if s.duration_seconds else '',
            'songId': s.pk,
            'url': s.audio_file.url if s.audio_file else '',
            'artist': ', '.join([
                localized_field(credit.person, 'full_name')
                for credit in s.credits.select_related('person').all() if credit.role in vocal_roles
            ]),
            'album': localized_field(s.album, 'title') if s.album else '',
        }
        for s in songs
    ]

    return JsonResponse({'songs': results})


_VOICE_INTENT_SYSTEM_PROMPT = """You are the voice-command intent classifier for an Arabic Tamer Hosny fan website's site-wide voice assistant. The user just spoke a short command, in Egyptian Arabic or English, right after saying a wake word - classify ONLY that command.

Respond with STRICT JSON ONLY (no markdown fences, no commentary) matching exactly this shape:
{
  "intent": one of "next", "previous", "stop", "resume", "seek_forward", "seek_backward", "like", "unlike", "open_current_song", "play_song", "play_mood", "play_lyrics", "play_album", "play_era", "play_random", "navigate", "unknown",
  "song_query": the song title/name mentioned (for play_song), or null,
  "mood": one of "ROMANTIC", "SAD_HEARTBREAK", "ENERGETIC_UPBEAT", "MOTIVATIONAL_HOPEFUL", "CHILL_RELAXING", "NOSTALGIC", "CONFIDENT_PLAYFUL" (for play_mood), or null,
  "lyrics_query": the lyrics phrase mentioned (for play_lyrics), or null,
  "album_query": the album name mentioned (for play_album), or null,
  "year": a specific 4-digit release year mentioned (for play_era), or null,
  "era": "OLD" or "RECENT" (for play_era, only when no specific year was given - "قديمة"/"old" -> OLD, "جديدة"/"حديثة"/"recent" -> RECENT), or null,
  "page": one of __PAGES__ (for navigate), or null
}

Guidance:
- next/previous are for switching to a whole different track (skip to another song).
- seek_forward/seek_backward are for moving a few seconds within the SAME song currently playing (e.g. "جري شوية"/"skip ahead a bit" vs "رجع شوية"/"rewind a bit") - never confuse these with next/previous.
- stop/resume are pause/play of the current song.
- like/unlike is about liking or unliking whatever song is currently playing.
- open_current_song means "open the page for whatever song is playing right now" - never pick this for a request naming a specific different song/album/person.
- play_song is for "play <specific song name>" - extract just the title into song_query.
- play_mood is for a request to play something matching a mood/feeling, not a specific title.
- play_lyrics is for a request to play a song containing specific lyrics/words - either explicitly framed (e.g. "كلمات فيها حب"/"غنية بتيقول يا حبيبي"/"song that says love") OR the user just singing/quoting an actual line from a song with no framing at all (e.g. "عايزك تعيديني يا حبيبتي"/"رزق من السنين وتملي تقولي لي") - a multi-word phrase (3+ words) that reads like a sung lyric rather than a command or a request phrased as one of the other intents should also be classified play_lyrics, with the full phrase as lyrics_query.
- play_album is for "play a song from album X" (e.g. "شغل أغنية من ألبوم لينا معاد"/"play something from album X") - extract just the album name into album_query.
- play_era is for a request by time period rather than a specific title/mood: a specific year ("شغل حاجة 2010"/"play something from 2010") -> put it in year; a vague "قديمة"/"من زمان"/"old" (no year given) -> era "OLD"; a vague "جديدة"/"حديثة"/"recent"/"new" (no year given) -> era "RECENT".
- play_random is for a request to just play *something* with no specific song, mood, album, or era given at all (e.g. "اقترح أغنية"/"suggest a song"/"شغل حاجة على ذوق"/"surprise me").
- navigate is ONLY for going to one of the fixed site sections listed above (never a specific song/album/person's own page - there is no intent for that; if the user asks for a specific item's page other than the current song, use "unknown").
- Use "unknown" whenever the command doesn't clearly and confidently fit one of the above.

Every key must be present; use null for any that don't apply to the chosen intent."""


def voice_intent(request):
    """Open-ended fallback for the voice assistant: once none of its
    fixed regex patterns match a command, the frontend posts the raw
    transcript here and gets back one classified intent from the same
    LLM fallback chain already used for song genre/mood classification
    (backend.music_app.shared_utils.song_classification) - reused as-is,
    just with a different prompt/schema.

    Deliberately narrow: the model only ever picks from a fixed intent
    list, a fixed mood list, and a fixed page list (never a raw URL/free
    text it makes up) - the frontend dispatches each intent to one
    pre-built handler, so a bad or hallucinated classification can only
    ever no-op or trigger the wrong *safe* action, never something
    arbitrary.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        body = json.loads(request.body or b'{}')
    except (ValueError, TypeError):
        return JsonResponse({'error': 'invalid JSON body'}, status=400)

    text = (body.get('text') or '').strip()[:300]
    if not text:
        return JsonResponse({'error': 'text is required'}, status=400)

    known = _find_known_phrase(text)
    if known:
        VoiceKnownPhrase.objects.filter(pk=known.pk).update(hit_count=F('hit_count') + 1)
        data = {
            'intent': known.intent,
            'song_query': known.song_query or None,
            'mood': known.mood or None,
            'lyrics_query': known.lyrics_query or None,
            'page': known.page or None,
        }
    else:
        system_prompt = _VOICE_INTENT_SYSTEM_PROMPT.replace('__PAGES__', str(list(VOICE_NAV_PAGES.keys())))
        data = ask_json(text, system_prompt, required_keys=('intent',)) or {}

    intent = data.get('intent') if data.get('intent') in VOICE_VALID_INTENTS else 'unknown'

    mood = data.get('mood')
    mood = mood if mood in Song.Mood.values else None

    lyrics_query = data.get('lyrics_query')
    lyrics_query = lyrics_query.strip() if isinstance(lyrics_query, str) and lyrics_query.strip() else None

    page_key = data.get('page')
    page_path = VOICE_NAV_PAGES.get(page_key)

    song_query = data.get('song_query')
    song_query = song_query.strip() if isinstance(song_query, str) and song_query.strip() else None

    album_query = data.get('album_query')
    album_query = album_query.strip() if isinstance(album_query, str) and album_query.strip() else None

    year = data.get('year')
    year = year if isinstance(year, int) and 1900 <= year <= 2100 else None

    era = data.get('era')
    era = era if era in ('OLD', 'RECENT') else None

    if intent == 'navigate' and not page_path:
        intent = 'unknown'
    if intent == 'play_mood' and not mood:
        intent = 'unknown'
    if intent == 'play_song' and not song_query:
        intent = 'unknown'
    if intent == 'play_lyrics' and not lyrics_query:
        intent = 'unknown'
    if intent == 'play_album' and not album_query:
        intent = 'unknown'
    if intent == 'play_era' and not year and not era:
        intent = 'unknown'

    # The classifier's "does this read like a sung lyric" call is
    # inconsistent in practice (real transcripts logged as unknown even
    # after the prompt above was made explicit about it) - a deterministic
    # backstop beats relying on the LLM to keep getting that judgment
    # right: nothing else matched, and it's long enough that it's far
    # more likely someone quoting/singing a line than a command we just
    # don't support yet.
    if intent == 'unknown' and len(text.split()) >= 3:
        intent = 'play_lyrics'
        lyrics_query = text

    return JsonResponse({
        'intent': intent,
        'song_query': song_query,
        'mood': mood,
        'lyrics_query': lyrics_query,
        'album_query': album_query,
        'year': year,
        'era': era,
        'page': page_path,
    })


def voice_log(request):
    """Diagnostic beacon for the voice assistant (see VoiceAssistantLog's
    docstring) - the browser posts here at each lifecycle event as it
    happens, purely so a pattern that's invisible server-side otherwise
    (mobile browsers tearing the whole recognition session down after
    nearly every utterance) can actually be inspected afterwards, in
    Django admin, instead of guessed at. Best-effort by design: a
    malformed or missing field just gets dropped/defaulted rather than
    erroring, since a failure here must never surface to the user or
    interrupt the assistant itself.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        body = json.loads(request.body or b'{}')
    except (ValueError, TypeError):
        return JsonResponse({'error': 'invalid JSON body'}, status=400)

    event_type = body.get('event_type')
    if event_type not in VoiceAssistantLog.EventType.values:
        return JsonResponse({'error': 'invalid event_type'}, status=400)

    ms_value = body.get('ms_value')
    ms_value = ms_value if isinstance(ms_value, int) else None
    transcript = str(body.get('transcript') or '')[:300]

    VoiceAssistantLog.objects.create(
        user=request.user if request.user.is_authenticated else None,
        client_session_id=str(body.get('session_id') or '')[:32],
        event_type=event_type,
        detail=str(body.get('detail') or '')[:255],
        transcript=transcript,
        ms_value=ms_value,
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
    )

    if event_type == 'COMMAND_FAILED' and transcript:
        # Analyzed in the background (AI classification + paraphrase
        # generation) and stored for voice_intent() to check on future
        # similarly-worded requests - see main_app.tasks.
        # analyze_failed_voice_command and VoiceKnownPhrase's docstring.
        # Queuing itself must never break this beacon endpoint (a
        # broker hiccup here is still just a missed learning
        # opportunity, same as everything else in this view).
        try:
            from backend.main_app.tasks import analyze_failed_voice_command
            analyze_failed_voice_command.delay(transcript)
        except Exception:
            pass

    return JsonResponse({'ok': True})


# ---------------------------------------------------------------------------
# People
# ---------------------------------------------------------------------------

def people_list(request):
    people = _paginate(request, Person.objects.all())
    top_ad, bottom_ad = _ad_slots(Advertisement.Placement.PEOPLE)
    return render(request, 'website/pages/people/list.html', {
        'people': people,
        'top_ad': top_ad,
        'bottom_ad': bottom_ad,
    })


def person_detail(request, slug):
    person = get_object_or_404(Person, slug=slug)
    song_credits = dedupe_credits(
        person.song_credits.select_related('song', 'song__album').order_by('-song__release_year'), 'song',
    )
    media_credits = dedupe_credits(
        person.media_credits.select_related('media').order_by('-media__release_date'), 'media',
        extra_label=lambda credit: credit.character_name,
    )
    related_people = Person.objects.exclude(pk=person.pk).order_by('?')[:6]
    top_ad, bottom_ad = _ad_slots(Advertisement.Placement.PEOPLE)
    return render(request, 'website/pages/people/detail.html', {
        'person': person,
        'song_credits': song_credits,
        'media_credits': media_credits,
        'links': person.links.select_related('platform').all(),
        'related_people': related_people,
        'top_ad': top_ad,
        'bottom_ad': bottom_ad,
    })


# ---------------------------------------------------------------------------
# Songs
# ---------------------------------------------------------------------------

def songs_list(request):
    queryset = Song.visible_queryset(Song.objects.select_related('album')).order_by('-release_year')
    songs = _paginate(request, queryset)
    top_ad, bottom_ad = _ad_slots(Advertisement.Placement.SONGS)
    return render(request, 'website/pages/songs/list.html', {
        'songs': songs,
        'top_ad': top_ad,
        'bottom_ad': bottom_ad,
    })


def song_detail(request, slug, duet_id=None):
    song = get_object_or_404(
        Song.objects.select_related('album', 'related_media', 'recording_studio'), slug=slug,
    )

    from backend.links_app.core.links import delete_fake_song_platform_links
    delete_fake_song_platform_links(song)

    # "غنيت إيه مع تامر" duets open on this exact same page: the same
    # layout, sections and player, just with the duet's own audio and
    # a small badge/actions swapped in for the hero.
    duet = None
    is_duet_owner = False

    if duet_id is not None:
        duet = get_object_or_404(
            SingWithTamerProject.objects.select_related('user'),
            pk=duet_id, song=song, is_completed=True,
        )
        is_duet_owner = request.user.is_authenticated and duet.user_id == request.user.id
        if not duet.is_public and not is_duet_owner:
            raise Http404

    duets = SingWithTamerProject.objects.filter(
        song=song, is_completed=True, is_public=True,
    ).exclude(final_audio_file='').select_related('user').order_by('-updated_at')[:12]

    user_other_duets = []
    discover_duets = []

    if duet is not None:
        user_other_duets = SingWithTamerProject.objects.filter(
            user=duet.user, is_completed=True, is_public=True,
        ).exclude(pk=duet.pk).exclude(final_audio_file='').select_related('song', 'song__album').order_by('-updated_at')[:12]

        discover_duets = SingWithTamerProject.objects.filter(
            is_completed=True, is_public=True,
        ).exclude(pk=duet.pk).exclude(song=song).exclude(final_audio_file='').select_related('song', 'song__album', 'user').order_by('-updated_at')[:12]


    # Auto-fetch lyrics if segments don't exist
    if not song.lyric_segments.exists():
        from backend.music_app.shared_utils.lyrics_fetcher import fetch_and_save_lyrics_for_song
        fetch_and_save_lyrics_for_song(song)
    
    album_songs = []
    
    if song.album_id:
        album_songs = Song.visible_queryset(
            Song.objects.filter(album_id=song.album_id).select_related('album')
        ).exclude(pk=song.pk)[:12]
    
    other_qs = Song.objects.select_related('album').exclude(pk=song.pk)
    if song.album_id:
        other_qs = other_qs.exclude(album_id=song.album_id)
    
    # Get songs from same type first
    same_type_songs = []
    if song.song_type:
        same_type_qs = other_qs.filter(song_type=song.song_type)
        same_type_songs = list(Song.visible_queryset(same_type_qs).order_by('?')[:6])
    
    # Get remaining songs from other types
    remaining_qs = other_qs
    if song.song_type:
        remaining_qs = remaining_qs.exclude(song_type=song.song_type)
    remaining_songs = list(Song.visible_queryset(remaining_qs).order_by('?')[:6])
    
    # Combine lists: same type first, then others
    other_songs = same_type_songs + remaining_songs

    # Precomputed (see main_app.shared_utils.song_recommendations) -
    # collaborative where enough people have listened to both, content
    # overlap otherwise. Falls back to its own random pick (not the
    # other_songs one above, a separate query) for a song that hasn't
    # been through a recompute yet (freshly added, or the nightly job
    # hasn't run since) - reusing other_songs verbatim here made both
    # sliders show the exact same songs whenever this fell back.
    recommended_songs = [
        row.similar_song for row in
        SongSimilarity.objects.filter(song=song).select_related('similar_song__album').order_by('rank')[:12]
    ]
    if not recommended_songs:
        recommended_songs = list(
            Song.visible_queryset(Song.objects.exclude(pk=song.pk).select_related('album')).order_by('?')[:12]
        )

    vocal_roles = (SongCredit.Role.SINGER, SongCredit.Role.FEATURED_ARTIST)
    all_credits = song.credits.select_related('person').all()
    singers = [credit for credit in all_credits if credit.role in vocal_roles]
    crew_credits = [credit for credit in all_credits if credit.role not in vocal_roles]

    # Check if user has favorited this song
    is_liked = False
    if request.user.is_authenticated:
        from django.contrib.contenttypes.models import ContentType
        song_ct = ContentType.objects.get_for_model(Song)
        is_liked = request.user.likes.filter(
            content_type=song_ct,
            object_id=song.pk
        ).exists()

    # Get like count
    from django.contrib.contenttypes.models import ContentType
    song_ct = ContentType.objects.get_for_model(Song)
    like_count = Like.objects.filter(content_type=song_ct, object_id=song.pk).count()

    listener_count = CurrentSongListener.objects.filter(song=song).count()

    top_ad, bottom_ad = _ad_slots(Advertisement.Placement.SONGS)

    if duet is not None:
        has_audio = bool(duet.final_audio_file) and duet.final_audio_file.storage.exists(duet.final_audio_file.name)
        audio_url = duet.final_audio_file.url if has_audio else ''
        performer_name = duet.user.get_full_name() or duet.user.username
        player_title = f'{localized_field(song, "title")} ({performer_name})'
    else:
        has_audio = bool(song.audio_file) and song.audio_file.storage.exists(song.audio_file.name)
        audio_url = song.audio_file.url if has_audio else ''
        player_title = localized_field(song, 'title')

    return render(request, 'website/pages/songs/detail.html', {
        'song': song,
        'singers': singers,
        'credits': dedupe_credits(crew_credits, 'person'),
        'links': song.links.select_related('platform').all(),
        'album_songs': album_songs,
        'other_songs': other_songs,
        'recommended_songs': recommended_songs,
        'top_ad': top_ad,
        'bottom_ad': bottom_ad,
        'is_liked': is_liked,
        'like_count': like_count,
        'listener_count': listener_count,
        'duet': duet,
        'is_duet_owner': is_duet_owner,
        'duets': duets,
        'user_other_duets': user_other_duets,
        'discover_duets': discover_duets,
        'audio_url': audio_url,
        'player_title': player_title,
    })


# ---------------------------------------------------------------------------
# Albums
# ---------------------------------------------------------------------------

def albums_list(request):
    queryset = Album.visible_queryset(Album.objects.all()).order_by('-release_date')
    albums = _paginate(request, queryset)
    top_ad, bottom_ad = _ad_slots(Advertisement.Placement.ALBUMS)
    return render(request, 'website/pages/albums/list.html', {
        'albums': albums,
        'top_ad': top_ad,
        'bottom_ad': bottom_ad,
    })


def album_detail(request, slug):
    album = get_object_or_404(Album, slug=slug)
    songs = Song.visible_queryset(album.songs.all())
    related_albums = Album.visible_queryset(Album.objects.exclude(pk=album.pk)).order_by('?')[:6]
    top_ad, bottom_ad = _ad_slots(Advertisement.Placement.ALBUMS)
    return render(request, 'website/pages/albums/detail.html', {
        'album': album,
        'songs': songs,
        'links': album.links.select_related('platform').all(),
        'related_albums': related_albums,
        'top_ad': top_ad,
        'bottom_ad': bottom_ad,
    })


# ---------------------------------------------------------------------------
# Media — movies, series and commercials are fully separate browse pages
# (though they share one Media model/detail template).
# ---------------------------------------------------------------------------

def _media_section_list(request, media_type, template_title):
    queryset = Media.visible_queryset(Media.objects.filter(media_type=media_type)).order_by('-release_date')
    media_items = _paginate(request, queryset)
    template = 'website/pages/media/list.html'
    if media_type == Media.MediaType.COMMERCIAL:
        template = 'website/pages/media/commercials_list.html'
    top_ad, bottom_ad = _ad_slots(Advertisement.Placement.MEDIA)
    return render(request, template, {
        'media_items': media_items,
        'list_title': template_title,
        'top_ad': top_ad,
        'bottom_ad': bottom_ad,
    })


def movies_list(request):
    return _media_section_list(request, Media.MediaType.MOVIE, _('الأفلام'))


def series_list(request):
    return _media_section_list(request, Media.MediaType.TV_SERIES, _('المسلسلات'))


def commercials_list(request):
    return _media_section_list(request, Media.MediaType.COMMERCIAL, _('الإعلانات والحملات الترويجية'))


def media_detail(request, slug):
    media = get_object_or_404(Media, slug=slug)
    related_media = Media.visible_queryset(
        Media.objects.filter(media_type=media.media_type).exclude(pk=media.pk)
    ).order_by('?')[:6]
    top_ad, bottom_ad = _ad_slots(Advertisement.Placement.MEDIA)
    return render(request, 'website/pages/media/detail.html', {
        'media': media,
        'credits': dedupe_credits(
            media.credits.select_related('person').all(), 'person',
            extra_label=lambda credit: credit.character_name,
        ),
        'links': media.links.select_related('platform').all(),
        'theme_songs': Song.visible_queryset(media.theme_songs.all()),
        'screenings': media.screenings.select_related('venue').all(),
        'related_media': related_media,
        'top_ad': top_ad,
        'bottom_ad': bottom_ad,
    })


# ---------------------------------------------------------------------------
# Concerts
# ---------------------------------------------------------------------------

def concerts_list(request):
    queryset = Concert.visible_queryset(Concert.objects.select_related('organizer')).order_by('-date')
    concerts = _paginate(request, queryset)
    top_ad, bottom_ad = _ad_slots(Advertisement.Placement.CONCERTS)
    return render(request, 'website/pages/concerts/list.html', {
        'concerts': concerts,
        'top_ad': top_ad,
        'bottom_ad': bottom_ad,
    })


def concert_detail(request, slug):
    concert = get_object_or_404(Concert, slug=slug)
    related_concerts = Concert.visible_queryset(
        Concert.objects.exclude(pk=concert.pk)
    ).order_by('?')[:6]
    top_ad, bottom_ad = _ad_slots(Advertisement.Placement.CONCERTS)
    return render(request, 'website/pages/concerts/detail.html', {
        'concert': concert,
        'links': concert.links.select_related('platform').all(),
        'related_concerts': related_concerts,
        'top_ad': top_ad,
        'bottom_ad': bottom_ad,
    })


# ---------------------------------------------------------------------------
# AI Remix
# ---------------------------------------------------------------------------

def remix_result(request, remix_id):
    """صفحة عرض نتيجة الريمكس"""
    project = get_object_or_404(RemixProject, id=remix_id)
    output = project.outputs.first()

    # الحصول على الأغاني المستخدمة من المصادر
    song1 = None
    song2 = None

    remix_sources = project.sources.all()
    if remix_sources.count() >= 2:
        # محاولة الحصول على الأغاني من أسماء المصادر
        source1_name = remix_sources[0].audio_source.name
        source2_name = remix_sources[1].audio_source.name

        # البحث عن الأغاني المطابقة
        song1 = Song.objects.filter(
            Q(title_ar__icontains=source1_name.replace(' (Audio)', '')) |
            Q(title_en__icontains=source1_name.replace(' (Audio)', ''))
        ).first()

        song2 = Song.objects.filter(
            Q(title_ar__icontains=source2_name.replace(' (Audio)', '')) |
            Q(title_en__icontains=source2_name.replace(' (Audio)', ''))
        ).first()

    return render(request, 'website/pages/remix_result.html', {
        'project': project,
        'output': output,
        'song1': song1,
        'song2': song2,
    })


# ---------------------------------------------------------------------------
# User Features - Favorites, Playlists, Remixes
# ---------------------------------------------------------------------------

@login_required
def list_playlists(request):
    """جلب قوائم التشغيل للمستخدم"""
    song_id = request.GET.get('song_id')
    playlists = Playlist.objects.filter(user=request.user).prefetch_related('items__song')
    playlist_data = []
    for playlist in playlists:
        songs = [item.song for item in playlist.items.all() if item.song]
        # Get up to 4 random songs with images
        import random
        random_songs = random.sample(songs, min(4, len(songs))) if songs else []
        images = []
        for song in random_songs:
            if song.cover_image:
                images.append(song.cover_image.url)
            elif song.album and song.album.cover_image:
                images.append(song.album.cover_image.url)
        
        # Check if current song is in playlist
        contains_song = False
        if song_id:
            contains_song = any(song.pk == int(song_id) for song in songs)
        
        playlist_data.append({
            'pk': playlist.pk,
            'name': playlist.name,
            'cover_image': playlist.cover_image.url if playlist.cover_image else None,
            'song_count': playlist.items.count(),
            'random_images': images,
            'contains_song': contains_song,
            'is_public': playlist.is_public
        })
    return JsonResponse({'status': 'success', 'playlists': playlist_data})


@login_required
@require_POST
def add_song_to_playlist(request):
    """إضافة أغنية لقائمة تشغيل موجودة"""
    playlist_id = request.POST.get('playlist_id')
    song_id = request.POST.get('song_id')
    
    if not playlist_id or not song_id:
        return JsonResponse({'status': 'error', 'message': 'Missing parameters'}, status=400)
    
    try:
        playlist = Playlist.objects.get(pk=playlist_id, user=request.user)
        song = Song.objects.get(pk=song_id)
        
        # Check if song already in playlist
        if PlaylistItem.objects.filter(playlist=playlist, song=song).exists():
            return JsonResponse({'status': 'error', 'message': 'Song already in playlist'}, status=400)
        
        # Add song to playlist
        max_order = PlaylistItem.objects.filter(playlist=playlist).aggregate(models.Max('order'))['order__max'] or 0
        PlaylistItem.objects.create(
            playlist=playlist,
            song=song,
            order=max_order + 1
        )
        
        return JsonResponse({'status': 'success'})
    except Playlist.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Playlist not found'}, status=404)
    except Song.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Song not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_POST
def create_playlist_with_song(request):
    """إنشاء قائمة تشغيل جديدة وإضافة أغنية تلقائياً"""
    name = request.POST.get('name')
    description = request.POST.get('description')
    mode = request.POST.get('mode')
    song_id = request.POST.get('song_id')
    
    if not name or not song_id:
        return JsonResponse({'status': 'error', 'message': 'Missing parameters'}, status=400)
    
    try:
        song = Song.objects.get(pk=song_id)
        
        # Create playlist
        playlist = Playlist.objects.create(
            user=request.user,
            name=name,
            description=description,
            is_public=mode == 'public'
        )
        
        # Add song to playlist
        PlaylistItem.objects.create(
            playlist=playlist,
            song=song,
            order=1
        )
        
        return JsonResponse({'status': 'success', 'playlist_id': playlist.pk})
    except Song.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Song not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_POST
def create_playlist(request):
    """إنشاء قائمة تشغيل جديدة"""
    name = request.POST.get('name')
    description = request.POST.get('description')
    is_public = request.POST.get('mode') == 'public'

    if not name:
        return JsonResponse({'status': 'error', 'message': 'Missing playlist name'}, status=400)

    try:
        playlist = Playlist.objects.create(
            user=request.user,
            name=name,
            description=description,
            is_public=is_public
        )
        return JsonResponse({'status': 'success', 'playlist_id': playlist.pk})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def playlists_list(request):
    """صفحة قوائم التشغيل - عرض جميع قوائم التشغيل للمستخدم"""
    playlists = Playlist.objects.filter(user=request.user).prefetch_related('items__song').order_by('-created_at')
    
    # Add random song images to each playlist
    for playlist in playlists:
        songs = [item.song for item in playlist.items.all() if item.song]
        # Get up to 4 random songs with images
        import random
        random_songs = random.sample(songs, min(4, len(songs))) if songs else []
        playlist.random_images = []
        for song in random_songs:
            if song.cover_image:
                playlist.random_images.append(song.cover_image.url)
            elif song.album and song.album.cover_image:
                playlist.random_images.append(song.album.cover_image.url)
    
    return render(request, 'website/pages/user/playlists.html', {
        'playlists': playlists,
    })


@login_required
@require_POST
def update_playlist(request, pk):
    """تحديث قائمة تشغيل"""
    playlist = get_object_or_404(Playlist, pk=pk, user=request.user)
    name = request.POST.get('name')
    description = request.POST.get('description')
    mode = request.POST.get('mode')
    
    if name:
        playlist.name = name
    if description is not None:
        playlist.description = description
    if mode:
        playlist.is_public = mode == 'public'
    
    playlist.save()
    return JsonResponse({'status': 'success'})


@login_required
@require_POST
def remove_song_from_playlist(request, pk):
    """حذف أغنية من قائمة تشغيل"""
    playlist = get_object_or_404(Playlist, pk=pk, user=request.user)
    item_id = request.POST.get('item_id')
    
    if not item_id:
        return JsonResponse({'status': 'error', 'message': 'Missing item_id'}, status=400)
    
    try:
        item = PlaylistItem.objects.get(pk=item_id, playlist=playlist)
        item.delete()
        return JsonResponse({'status': 'success'})
    except PlaylistItem.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Item not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def playlist_detail(request, pk):
    """صفحة تفاصيل قائمة التشغيل"""
    playlist = get_object_or_404(Playlist, pk=pk, user=request.user)
    items = playlist.items.select_related('song__album').order_by('order')
    return render(request, 'website/pages/user/playlist_detail.html', {
        'playlist': playlist,
        'items': items,
    })


@login_required
def remixes_list(request):
    """صفحة الريمكسات - عرض جميع مشاريع الريمكس للمستخدم"""
    # لاحقاً: ربط RemixProject بالمستخدم
    # حالياً: عرض جميع المشاريع
    queryset = RemixProject.objects.prefetch_related('sources__audio_source', 'outputs').order_by('-created_at')

    projects = _paginate(request, queryset)

    # إضافة مدة منسقة وأسماء الأغاني وصورها لكل مشروع
    for project in projects:
        output = project.outputs.first()
        if output and output.duration:
            duration = output.duration
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            project.formatted_duration = f"{minutes}:{seconds:02d}"
        else:
            project.formatted_duration = None

        # جمع أسماء الأغاني والبحث عن صورها من المصادر الصوتية
        song_names = []
        song_images = []
        for source in project.sources.all():
            song_name = source.audio_source.name
            song_names.append(song_name)

            # البحث عن الأغنية المطابقة للحصول على صورتها
            song = Song.objects.filter(
                Q(title_ar__icontains=song_name.replace(' (Audio)', '')) |
                Q(title_en__icontains=song_name.replace(' (Audio)', ''))
            ).first()

            if song:
                if song.cover_image:
                    song_images.append(song.cover_image.url)
                elif song.album and song.album.cover_image:
                    song_images.append(song.album.cover_image.url)
                else:
                    song_images.append(None)
            else:
                song_images.append(None)

        project.song_names = ', '.join(song_names)
        project.song_images = song_images

    return render(request, 'website/pages/user/remixes.html', {
        'projects': projects,
    })


@require_POST
def record_full_listen(request):
    """Called from the player's native 'ended' event - a song reached
    its natural end (not a skip/pause), which is the one signal that
    should move the "top listeners" leaderboard.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'success', 'recorded': False})

    song_id = request.POST.get('song_id')
    if not song_id or not Song.objects.filter(pk=song_id).exists():
        return JsonResponse({'status': 'error', 'message': 'Invalid song_id'}, status=400)

    from backend.main_app.shared_utils.song_leaderboard import record_full_listen as _record
    _record(request.user, song_id)

    return JsonResponse({'status': 'success', 'recorded': True})


@require_POST
def increment_play_count(request):
    """زيادة عدد مرات التشغيل للأغنية (فقط إذا مرت ساعة على آخر تشغيل للمستخدم)"""
    song_id = request.POST.get('song_id')
    
    if not song_id:
        return JsonResponse({'status': 'error', 'message': 'Missing song_id'}, status=400)
    
    try:
        
        song = Song.objects.get(pk=song_id)

        # A duet play isn't a play of the official track - don't count it
        # (moved here from the one caller that used to check this
        # client-side, so it holds no matter which play path calls this).
        if song.is_duet:
            return JsonResponse({'status': 'success', 'play_count': song.play_count, 'incremented': False})

        # Only track logged in users
        if not request.user.is_authenticated:
            return JsonResponse({'status': 'success', 'play_count': song.play_count, 'incremented': False})
        
        # Get or create UserSongPlay for this user and song
        user_play, created = UserSongPlay.objects.get_or_create(
            user=request.user,
            song=song
        )
        
        # Check if last play was more than 1 hour ago
        if not created and user_play.last_played_at:
            time_since_last_play = timezone.now() - user_play.last_played_at
            if time_since_last_play < timedelta(hours=1):
                # Less than 1 hour since last play, don't increment
                return JsonResponse({'status': 'success', 'play_count': song.play_count, 'incremented': False})
        
        # Increment song play count and user play count
        song.play_count += 1
        song.save(update_fields=['play_count'])
        
        user_play.play_count += 1
        user_play.last_played_at = timezone.now()
        user_play.save()

        return JsonResponse({'status': 'success', 'play_count': song.play_count, 'incremented': True})
    except Song.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Song not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


SING_WITH_TAMER_COOLDOWN = timedelta(hours=24)


# "Guess the song" daily challenge - one song a day, six tries, each
# wrong guess reveals a longer clip (same idea as Heardle/Wordle). The
# clip itself is never trimmed server-side - the browser just pauses
# playback at `revealed_seconds`, so the full audio file stays the one
# already served for the normal song page; nothing extra to compute or
# store per attempt.
DAILY_GUESS_REVEAL_SCHEDULE = [6]
DAILY_GUESS_MAX_ATTEMPTS = len(DAILY_GUESS_REVEAL_SCHEDULE)
DAILY_GUESS_NO_REPEAT_DAYS = 30

# A different compliment on a correct guess, so winning doesn't always
# show the exact same line - shown inside the result card.
DAILY_GUESS_WIN_LINES = [
    _('شكلك حافظ كل أغاني تامر عن ظهر قلب 🎤'),
    _('ده انت من جمهور تامر الأصليين فعلاً 👏'),
    _('عارفها من أول ثانية؟ يبقى انت جمهور VIP'),
    _('احترافية! مفيش حد يفوتك في أغاني تامر'),
    _('تمام كده، ذوقك في الأغاني موزون'),
    _('ماشاء الله عليك، ودنك موسيقية فعلاً 🎧'),
    _('برافو، ده مستوى المحترفين'),
    _('واضح إنك سامع تامر من زمان'),
    _('يا سلام، خمّنتها بسهولة!'),
    _('أنت فعلاً من عيلة تامر حسني الكبيرة'),
    _('حاسس إنك حافظ الألبومات كلها؟ 😄'),
    _('جميل جدًا، جايبها من أول محاولة'),
    _('ذوقك الموسيقي عالي جدًا'),
    _('كده تستاهل تاج جمهور تامر 👑'),
    _('مستحيل حد يغلبك في اللعبة دي'),
    _('شكلك بتسمع تامر كل يوم صح؟'),
    _('عارف كل نغمة قبل ما تخلص 🎶'),
    _('برافو عليك، ده تحدي مش سهل وعديته'),
    _('واثق من نفسك واخترت صح - عاش'),
    _('ده مستوى تاني خالص، تحفة'),
]


def _daily_guess_pick_song(exclude_ids=()):
    eligible = Song.objects.filter(audio_file__isnull=False).exclude(audio_file='')
    return eligible.exclude(pk__in=exclude_ids).order_by('?').first() or eligible.order_by('?').first()


def _daily_guess_song_title(song):
    """song's own __str__ always returns title_ar - the guess game shows
    names in whichever language the visitor is browsing in instead."""
    if get_language() == 'en':
        return song.title_en or song.title_ar
    return song.title_ar or song.title_en


def _get_or_create_daily_challenge(today, user):
    """Each signed-in user gets their own random song for the day -
    stored per (date, user) so it stays the same across refreshes and
    devices, but two different users opening the game the same day
    almost certainly get different songs.
    """
    challenge = DailyGuessChallenge.objects.filter(date=today, user=user).select_related('song').first()
    if challenge:
        return challenge

    recent_song_ids = list(
        DailyGuessChallenge.objects.filter(user=user).order_by('-date')[:DAILY_GUESS_NO_REPEAT_DAYS]
        .values_list('song_id', flat=True)
    )
    song = _daily_guess_pick_song(exclude_ids=recent_song_ids)
    if not song:
        return None

    challenge, _created = DailyGuessChallenge.objects.get_or_create(date=today, user=user, defaults={'song': song})
    return challenge


def _daily_guess_session_key(today):
    return f'daily_guess_{today.isoformat()}'


def _daily_guess_clip_start_seconds(song):
    """The reveal clip should be a melody/instrumental hook, not a
    spoken-out clue - starting it inside a LYRICS segment plays the
    actual sung words, which straight up gives the song away. Starts at
    the first MUSIC-type segment long enough (> 5s) to hold the whole
    reveal window without running into whatever comes right after it.
    """
    qualifying_music = (
        song.lyric_segments.filter(segment_type='MUSIC')
        .annotate(segment_duration=F('end_seconds') - F('start_seconds'))
        .filter(segment_duration__gt=5)
        .order_by('start_seconds')
        .first()
    )
    if qualifying_music:
        return float(qualifying_music.start_seconds)

    # No usable lyrics timing for this song - starting at 0:00 blind
    # often lands right on a silent instrumental intro instead of any
    # actual audible content, so jump a bit into the track instead
    # (a guess at "past the intro", capped so it can't be later than
    # the tail end of a short song).
    if song.duration_seconds:
        return min(float(song.duration_seconds) * 0.2, 30.0)
    return 15.0


def _daily_guess_build_choices(song):
    """Correct answer + 2 random wrong songs (just their ids), shuffled
    once and then kept fixed for this session (stored alongside the
    rest of the game state) - regenerating them on every request would
    let someone just refresh until the correct one is obviously the odd
    one out, and would also reshuffle the options mid-game.

    Only ids are stored, not display titles: the visitor can switch the
    site's language mid-round, and a title baked in at build time would
    stay frozen in whichever language was active then - _daily_guess_
    resolve_choices looks titles up fresh, in the current language,
    every time the choices are actually displayed.
    """
    distractor_ids = list(
        Song.objects.filter(audio_file__isnull=False).exclude(audio_file='')
        .exclude(pk=song.pk).order_by('?')[:2].values_list('pk', flat=True)
    )
    choice_ids = [song.pk] + distractor_ids
    random.shuffle(choice_ids)
    return choice_ids


def _daily_guess_resolve_choices(song_ids):
    songs_by_id = Song.objects.in_bulk(song_ids)
    return [
        {'id': song_id, 'title': _daily_guess_song_title(songs_by_id[song_id])}
        for song_id in song_ids if song_id in songs_by_id
    ]


def daily_guess_game(request):
    """صفحة لعبة 'خمّن الأغنية' اليومية - كل يوزر بياخد أغنية عشوائية
    مختلفة، مش نفس الأغنية لكل الناس."""
    today = timezone.localdate()
    session_key = _daily_guess_session_key(today)
    state = request.session.get(session_key)

    # A signed-in user's song is authoritative from the DB (so it stays
    # identical across devices/tabs); an anonymous visitor has no DB row
    # at all, so whatever is already in their session is authoritative
    # instead. Either way this resolves the ONE song this request should
    # use, before touching session state at all.
    if request.user.is_authenticated:
        challenge = _get_or_create_daily_challenge(today, request.user)
        if challenge is None:
            return render(request, 'website/pages/daily_guess.html', {'no_songs': True})
        song = challenge.song
    elif state is not None:
        song = Song.objects.filter(pk=state.get('song_id')).select_related('album').first()
    else:
        song = None

    if song is None:
        song = _daily_guess_pick_song()
        if song is None:
            return render(request, 'website/pages/daily_guess.html', {'no_songs': True})

    # Reset the in-progress state if it's missing, stale (pointed at a
    # song that's since been deleted), no longer matches the song just
    # resolved above (e.g. logging in revealed a different song already
    # assigned to this account on another device), or - belt and braces
    # against any future bug shaped like this one - its own choices
    # don't actually contain that song, which would make the round
    # unguessable no matter what the player picks.
    choices_include_song = song.pk in state['choices'] if state else False
    if state is None or state.get('song_id') != song.pk or not choices_include_song:
        state = {'song_id': song.pk, 'guesses': [], 'won': False, 'lost': False}
        state['choices'] = _daily_guess_build_choices(song)
        request.session[session_key] = state
        request.session.modified = True

    # A guess is only ever recorded once someone is logged in (see
    # daily_guess_attempt), and the DB row is the source of truth for a
    # signed-in visitor - not the session:
    # - restores a finished result into the session for a new
    #   session/device (a private tab, clearing cookies) so it can't be
    #   replayed just by losing the old session.
    # - resets an in-progress-looking session back to "not played yet"
    #   if the DB attempt is gone (a dashboard admin cleared it), so a
    #   cleared player isn't stuck seeing their old cached result.
    if request.user.is_authenticated:
        existing_attempt = DailyGuessAttempt.objects.filter(user=request.user, challenge=challenge).first()
        if existing_attempt is not None and not (state['won'] or state['lost']):
            state['guesses'] = [{
                'song_id': existing_attempt.guessed_song_id,
                'title': _daily_guess_song_title(existing_attempt.guessed_song),
                'correct': existing_attempt.correct,
            }]
            state['won'] = existing_attempt.correct
            state['lost'] = not existing_attempt.correct
            if state['won']:
                state['win_line_index'] = existing_attempt.hype_line_index
            request.session[session_key] = state
            request.session.modified = True
        elif existing_attempt is None and (state['won'] or state['lost']):
            state = {'song_id': song.pk, 'guesses': [], 'won': False, 'lost': False}
            state['choices'] = _daily_guess_build_choices(song)
            request.session[session_key] = state
            request.session.modified = True

    attempts_used = len(state['guesses'])
    finished = state['won'] or state['lost']

    if finished:
        revealed_seconds = float(song.duration_seconds or DAILY_GUESS_REVEAL_SCHEDULE[-1])
        answer = {
            'title': _daily_guess_song_title(song),
            'slug': song.slug,
            'cover_url': song.display_cover_url,
        }
    else:
        revealed_seconds = DAILY_GUESS_REVEAL_SCHEDULE[min(attempts_used, DAILY_GUESS_MAX_ATTEMPTS - 1)]
        answer = None

    return render(request, 'website/pages/daily_guess.html', {
        'audio_url': song.audio_file.url,
        'clip_start_seconds': _daily_guess_clip_start_seconds(song),
        'revealed_seconds': revealed_seconds,
        'attempts_used': attempts_used,
        'max_attempts': DAILY_GUESS_MAX_ATTEMPTS,
        'guesses': state['guesses'],
        'won': state['won'],
        'lost': state['lost'],
        'finished': finished,
        'answer': answer,
        'reveal_schedule': DAILY_GUESS_REVEAL_SCHEDULE,
        'choices': _daily_guess_resolve_choices(state['choices']),
        'hype_line': (
            DAILY_GUESS_WIN_LINES[state['win_line_index'] % len(DAILY_GUESS_WIN_LINES)]
            if state['won'] and state.get('win_line_index') is not None else None
        ),
    })


@require_POST
def daily_guess_track(request):
    """بيسجل كل مرة اللاعب دوس Play وكل ثانية سمعها فعليًا، عشان نقط
    الفوز تتحسب بعدين على أساس قد إيه احتاج يسمع - مش لازم تسجيل دخول
    هنا لسه (الزائر ممكن يجرب قبل ما يسجل)، بس من غير تسجيل دخول القيم
    دي مش هتتحول لنقط فعلية أبدًا."""
    today = timezone.localdate()
    session_key = _daily_guess_session_key(today)
    state = request.session.get(session_key)
    if state is None:
        return JsonResponse({'error': 'no active round'}, status=400)

    if not (state['won'] or state['lost']):
        event = request.POST.get('event')
        if event == 'play':
            state['play_count'] = state.get('play_count', 0) + 1
            request.session[session_key] = state
            request.session.modified = True
        elif event == 'listened':
            try:
                seconds = max(0.0, float(request.POST.get('seconds', 0)))
            except (TypeError, ValueError):
                seconds = 0.0
            state['seconds_listened'] = state.get('seconds_listened', 0) + seconds
            request.session[session_key] = state
            request.session.modified = True

    return JsonResponse({'status': 'ok'})


@require_POST
def daily_guess_attempt(request):
    """معالجة محاولة تخمين واحدة - لازم تسجيل دخول عشان المحاولة تتنسب لليوزر."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'login_required'}, status=401)

    today = timezone.localdate()
    challenge = _get_or_create_daily_challenge(today, request.user)
    if challenge is None:
        return JsonResponse({'error': 'no songs available'}, status=400)

    if DailyGuessAttempt.objects.filter(user=request.user, challenge=challenge).exists():
        return JsonResponse({'error': 'already finished'}, status=400)

    session_key = _daily_guess_session_key(today)
    state = request.session.get(session_key)
    if state is None:
        return JsonResponse({'error': 'open the game page first'}, status=400)

    if state['won'] or state['lost']:
        return JsonResponse({'error': 'already finished'}, status=400)
    if len(state['guesses']) >= DAILY_GUESS_MAX_ATTEMPTS:
        return JsonResponse({'error': 'no attempts left'}, status=400)

    try:
        guessed_song_id = int(request.POST.get('song_id', ''))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'invalid song_id'}, status=400)

    # Only one of the 3 choices actually shown to this session is a
    # valid guess.
    if guessed_song_id not in state['choices']:
        return JsonResponse({'error': 'not one of the shown choices'}, status=400)
    guessed_song = get_object_or_404(Song, pk=guessed_song_id)

    is_correct = guessed_song_id == challenge.song_id
    state['guesses'].append({'song_id': guessed_song_id, 'title': _daily_guess_song_title(guessed_song), 'correct': is_correct})

    # Picked once here (not re-rolled on every render) and stored on both
    # the session and the attempt row itself, so a page refresh - or
    # looking back at this day's history later - always shows the exact
    # same compliment instead of a new random one each time.
    hype_line_index = random.randrange(len(DAILY_GUESS_WIN_LINES)) if is_correct else None

    play_count = int(state.get('play_count', 0))
    seconds_listened = int(state.get('seconds_listened', 0))
    # Genuinely listening is worth more, not less: hitting play and
    # guessing after only a second or two of actual audio is exactly
    # the "barely engaged" behavior this is meant to discourage, so
    # more plays and more seconds actually listened both raise the
    # score - each capped so looping the clip forever can't inflate it
    # without limit.
    points_awarded = 20 + min(play_count, 10) * 10 + min(seconds_listened, 60) * 3 if is_correct else 0

    DailyGuessAttempt.objects.create(
        user=request.user, challenge=challenge, guessed_song_id=guessed_song_id, correct=is_correct,
        hype_line_index=hype_line_index, play_count=play_count, seconds_listened=seconds_listened,
        points_awarded=points_awarded,
    )

    if is_correct:
        state['won'] = True
        state['win_line_index'] = hype_line_index
        award_points(request.user, points_awarded)
    elif len(state['guesses']) >= DAILY_GUESS_MAX_ATTEMPTS:
        state['lost'] = True
        award_points(request.user, POINTS_GUESS_LOSS)

    request.session[session_key] = state
    request.session.modified = True

    finished = state['won'] or state['lost']
    attempts_used = len(state['guesses'])

    if finished:
        revealed_seconds = float(challenge.song.duration_seconds or DAILY_GUESS_REVEAL_SCHEDULE[-1])
        answer = {
            'title': _daily_guess_song_title(challenge.song),
            'slug': challenge.song.slug,
            'cover_url': challenge.song.display_cover_url,
        }
    else:
        revealed_seconds = DAILY_GUESS_REVEAL_SCHEDULE[min(attempts_used, DAILY_GUESS_MAX_ATTEMPTS - 1)]
        answer = None

    return JsonResponse({
        'correct': is_correct,
        'finished': finished,
        'won': state['won'],
        'attempts_used': attempts_used,
        'revealed_seconds': revealed_seconds,
        'answer': answer,
    })


def daily_guess_history(request):
    """أيام 'خمّن الأغنية' اللي اليوزر لعبها - وكسب فيها ولا خسر."""
    if not request.user.is_authenticated:
        return redirect('website_app:home')

    attempts = DailyGuessAttempt.objects.filter(user=request.user).select_related(
        'challenge__song',
    ).order_by('-challenge__date')
    return render(request, 'website/pages/daily_guess_history.html', {
        'attempts': attempts,
    })


def daily_guess_history_day(request, date):
    """نتيجة يوم معين من أيام اللعب - بتستخدم نفس صفحة اللعبة نفسها في
    وضع 'خلصت اللعبة' بدل ما تكون صفحة منفصلة."""
    if not request.user.is_authenticated:
        return redirect('website_app:home')

    try:
        day = datetime.strptime(date, '%Y-%m-%d').date()
    except ValueError:
        raise Http404

    attempt = get_object_or_404(
        DailyGuessAttempt.objects.select_related('challenge__song', 'guessed_song'),
        user=request.user, challenge__date=day,
    )
    song = attempt.challenge.song
    hype_line = None
    if attempt.correct:
        line_index = attempt.hype_line_index
        if line_index is None:
            line_index = attempt.pk % len(DAILY_GUESS_WIN_LINES)
        hype_line = DAILY_GUESS_WIN_LINES[line_index]

    return render(request, 'website/pages/daily_guess.html', {
        'audio_url': song.audio_file.url if song.audio_file else '',
        'clip_start_seconds': _daily_guess_clip_start_seconds(song),
        'revealed_seconds': float(song.duration_seconds or DAILY_GUESS_REVEAL_SCHEDULE[-1]),
        'attempts_used': 1,
        'max_attempts': DAILY_GUESS_MAX_ATTEMPTS,
        'guesses': [{
            'song_id': attempt.guessed_song_id,
            'title': _daily_guess_song_title(attempt.guessed_song),
            'correct': attempt.correct,
        }],
        'won': attempt.correct,
        'lost': not attempt.correct,
        'finished': True,
        'answer': {
            'title': _daily_guess_song_title(song),
            'slug': song.slug,
            'cover_url': song.display_cover_url,
        },
        'reveal_schedule': DAILY_GUESS_REVEAL_SCHEDULE,
        'choices': [],
        'hype_line': hype_line,
    })


def sing_with_tamer(request, slug):
    """صفحة غني مع تامر - للغناء مع الأغنية"""
    song = get_object_or_404(
        Song.objects.select_related('album'), slug=slug,
    )

    # Auto-fetch lyrics if segments don't exist
    if not song.lyric_segments.exists():
        from backend.music_app.shared_utils.lyrics_fetcher import fetch_and_save_lyrics_for_song
        fetch_and_save_lyrics_for_song(song)

    vocal_roles = (SongCredit.Role.SINGER, SongCredit.Role.FEATURED_ARTIST)
    all_credits = song.credits.select_related('person').all()
    singers = [credit for credit in all_credits if credit.role in vocal_roles]

    # Already recorded this exact song - show that recording instead of
    # letting them start over. Otherwise, a completed recording of *any*
    # other song within the last 24h blocks starting a new one until the
    # cooldown clears (one duet per day, site-wide - not per song).
    existing_project = None
    cooldown_hours_left = None
    if request.user.is_authenticated:
        existing_project = SingWithTamerProject.objects.filter(
            user=request.user, song=song, is_completed=True,
        ).order_by('-created_at').first()

        if not existing_project:
            last_project = SingWithTamerProject.objects.filter(
                user=request.user, is_completed=True,
            ).order_by('-created_at').first()
            if last_project:
                elapsed = timezone.now() - last_project.created_at
                if elapsed < SING_WITH_TAMER_COOLDOWN:
                    remaining = SING_WITH_TAMER_COOLDOWN - elapsed
                    cooldown_hours_left = max(1, int(remaining.total_seconds() // 3600) + 1)

    return render(request, 'website/pages/sing-with-tamer/index.html', {
        'song': song,
        'singers': singers,
        'existing_project': existing_project,
        'cooldown_hours_left': cooldown_hours_left,
    })


@login_required
@require_POST
def toggle_favorite(request):
    """تبديل حالة الإعجاب بالمحتوى"""
    content_type = request.POST.get('content_type')
    object_id = request.POST.get('object_id')
    check_only = request.POST.get('check_only') == 'true'
    
    if not content_type or not object_id:
        return JsonResponse({'status': 'error', 'message': 'Missing parameters'}, status=400)
    
    try:
        # الحصول على ContentType
        ct = ContentType.objects.get(model=content_type.lower())
        
        # الحصول على الكائن
        obj = ct.get_object_for_this_type(pk=object_id)
        
        if check_only:
            # فقط التحقق من حالة الإعجاب
            like = Like.objects.filter(
                user=request.user,
                content_type=ct,
                object_id=object_id
            ).first()
            return JsonResponse({'status': 'success', 'liked': like is not None})
        
        # التحقق من وجود الإعجاب
        like, created = Like.objects.get_or_create(
            user=request.user,
            content_type=ct,
            object_id=object_id
        )
        
        if not created:
            # إذا كان موجوداً، احذفه
            like.delete()
            liked = False
        else:
            # إذا لم يكن موجوداً، تم إنشاؤه
            liked = True

        if content_type.lower() == 'song':
            from backend.main_app.shared_utils.song_leaderboard import refresh_song_leaderboard
            refresh_song_leaderboard(object_id)

        if liked:
            award_points(request.user, POINTS_LIKE)

        return JsonResponse({'status': 'success', 'liked': liked})

    except ContentType.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Invalid content type'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def likes_list(request):
    """عرض قائمة الإعجاب للمستخدم"""
    likes = Like.objects.filter(user=request.user).select_related('content_type').prefetch_related('content_object')
    
    # فصل المحتوى حسب النوع
    songs = []
    media_items = []
    concerts = []
    
    for like in likes:
        if like.content_type.model == 'song':
            songs.append(like.content_object)
        elif like.content_type.model == 'media':
            media_items.append(like.content_object)
        elif like.content_type.model == 'concert':
            concerts.append(like.content_object)
    
    return render(request, 'website/pages/user/favorites.html', {
        'songs': songs,
        'media_items': media_items,
        'concerts': concerts,
    })


@login_required
def my_duets_list(request):
    """عرض ثنائيات 'غني مع تامر' الخاصة بالمستخدم فقط"""
    duets = SingWithTamerProject.objects.filter(
        user=request.user,
        is_completed=True,
    ).exclude(final_audio_file='').select_related('song').order_by('-updated_at')

    # Still-mixing duets (the Celery task hasn't finished/failed yet) -
    # shown as a "still creating" placeholder instead of just vanishing
    # from this page until the mix completes.
    processing_duets = SingWithTamerProject.objects.filter(
        user=request.user,
        processing_status=SingWithTamerProject.ProcessingStatus.PROCESSING,
    ).select_related('song').order_by('-updated_at')

    return render(request, 'website/pages/user/duets.html', {
        'duets': duets,
        'processing_duets': processing_duets,
    })


PROFILE_PREVIEW_SIZE = 12


def public_profile(request, username):
    """صفحة عامة تظهر لأي زائر - إحصائيات ونشاط المستخدم اللي هو نفسه
    اختار مشاركتها (ثنائيات 'غني مع تامر' العامة فقط، مش الخاصة).

    "الأكثر استماعاً" و"المفضلة" بيتعرضوا هنا كمعاينة سلايدر بس (أول
    PROFILE_PREVIEW_SIZE عنصر) - عرض القائمة كاملة على طول كان بيكسر
    شكل الصفحة لو المستخدم عنده مية أغنية مفضلة مثلاً؛ "عرض المزيد"
    بياخد لصفحة مخصصة فيها القائمة كاملة بترقيم صفحات أثناء التمرير.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    profile_user = get_object_or_404(User, username=username)

    liked_songs_qs = Like.objects.filter(
        user=profile_user, content_type__model='song',
    ).select_related('content_type')
    liked_songs_total = liked_songs_qs.count()
    liked_songs = [
        like.content_object for like in liked_songs_qs[:PROFILE_PREVIEW_SIZE]
        if like.content_object is not None
    ]

    public_duets = SingWithTamerProject.objects.filter(
        user=profile_user, is_completed=True, is_public=True,
    ).exclude(final_audio_file='').select_related('song').order_by('-updated_at')

    full_listens_qs = UserSongPlay.objects.filter(
        user=profile_user, full_listen_count__gt=0,
    ).select_related('song', 'song__album').order_by('-decayed_score')
    full_listens_total = full_listens_qs.count()
    full_listens = full_listens_qs[:PROFILE_PREVIEW_SIZE]

    game_profile = UserGameProfile.objects.filter(user=profile_user).first()
    game_badges = unlocked_badges(game_profile) if game_profile else []
    game_rank, game_rank_trend = get_rank_and_trend(game_profile) if game_profile else (None, None)

    return render(request, 'website/pages/user/public_profile.html', {
        'profile_user': profile_user,
        'liked_songs': liked_songs,
        'liked_songs_total': liked_songs_total,
        'public_duets': public_duets,
        'full_listens': full_listens,
        'full_listens_total': full_listens_total,
        'is_own_profile': request.user.is_authenticated and request.user.pk == profile_user.pk,
        'game_profile': game_profile,
        'game_badges': game_badges,
        'game_rank': game_rank,
        'game_rank_trend': game_rank_trend,
    })


def leaderboard(request):
    """ترتيب أكتر المستخدمين نقط - بتتجمع من كل نشاط في الموقع (خمّن
    الأغنية، الإعجابات، الدويتوهات...) في نفس البروفايل."""
    top_profiles = UserGameProfile.objects.select_related('user').filter(points__gt=0)[:50]

    my_profile = None
    my_rank = None
    if request.user.is_authenticated:
        my_profile = UserGameProfile.objects.filter(user=request.user).first()
        if my_profile:
            my_rank = UserGameProfile.objects.filter(points__gt=my_profile.points).count() + 1

    return render(request, 'website/pages/leaderboard.html', {
        'top_profiles': top_profiles,
        'my_profile': my_profile,
        'my_rank': my_rank,
    })


def profile_most_listened(request, username):
    """القائمة الكاملة لأكتر أغاني استمعلها المستخدم - بترقيم صفحات
    أثناء التمرير (الطلب الأول بيرجع الصفحة كاملة، وأي طلب AJAX تالي
    بيرجع بطاقات الأغاني بس عشان JS يضيفها تحت الموجودة).
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    profile_user = get_object_or_404(User, username=username)

    qs = UserSongPlay.objects.filter(
        user=profile_user, full_listen_count__gt=0,
    ).select_related('song', 'song__album').order_by('-decayed_score')
    page_obj = _paginate(request, qs)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'html': render_to_string(
                'website/partials/_profile_most_listened_items.html',
                {'full_listens': page_obj}, request=request,
            ),
            'has_next': page_obj.has_next(),
        })

    return render(request, 'website/pages/user/profile_most_listened.html', {
        'profile_user': profile_user,
        'full_listens': page_obj,
        'has_next': page_obj.has_next(),
    })


def profile_favorites(request, username):
    """القائمة الكاملة للأغاني المفضلة عند المستخدم - نفس فكرة الترقيم
    أثناء التمرير في profile_most_listened."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    profile_user = get_object_or_404(User, username=username)

    qs = Like.objects.filter(
        user=profile_user, content_type__model='song',
    ).select_related('content_type').order_by('-created_at')
    page_obj = _paginate(request, qs)
    songs = [like.content_object for like in page_obj if like.content_object is not None]

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'html': render_to_string(
                'website/partials/_profile_favorites_items.html',
                {'liked_songs': songs}, request=request,
            ),
            'has_next': page_obj.has_next(),
        })

    return render(request, 'website/pages/user/profile_favorites.html', {
        'profile_user': profile_user,
        'liked_songs': songs,
        'has_next': page_obj.has_next(),
    })


@login_required
@require_POST
def update_profile(request):
    """يعدّل المستخدم اسمه و/أو صورته من صفحة بروفايله بس - مفيش حد تاني
    يقدر يعدل غير حسابه هو (login_required كافي هنا لأننا دايماً بنعدل
    request.user، مش أي id متبعت من الفورم). AJAX بالكامل - بيرجع JSON
    مش redirect، عشان الصفحة تتحدث من غير ريفريش.
    """
    if request.POST.get('remove_image') == '1':
        request.user.profile_image.delete(save=False)
        request.user.profile_image = None
        request.user.save(update_fields=['profile_image'])
        return JsonResponse({'status': 'success', 'username': request.user.username, 'avatar_url': None})

    new_username = (request.POST.get('username') or '').strip()
    if new_username and new_username != request.user.username:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if User.objects.exclude(pk=request.user.pk).filter(username=new_username).exists():
            return JsonResponse({'status': 'error', 'message': str(_('اسم المستخدم ده مأخوذ بالفعل.'))}, status=400)
        request.user.username = new_username

    if request.FILES.get('profile_image'):
        request.user.profile_image = request.FILES['profile_image']

    request.user.save()
    return JsonResponse({
        'status': 'success',
        'username': request.user.username,
        'avatar_url': request.user.profile_image.url if request.user.profile_image else None,
    })


@login_required
@require_POST
def toggle_duet_privacy(request, pk):
    """تبديل حالة الثنائي بين عام وخاص - لصاحبه فقط"""
    duet = get_object_or_404(SingWithTamerProject, pk=pk, user=request.user)
    duet.is_public = not duet.is_public
    duet.save(update_fields=['is_public'])
    return JsonResponse({'status': 'success', 'is_public': duet.is_public})


def recap(request, username):
    """ملخص شخصي وقابل للمشاركة لنشاط مستخدم على الأرشيف - بديل عن
    "Spotify Wrapped" لكن بدون تقييد بسنة معينة: UserSongPlay بيحتفظ
    بصف واحد لكل (مستخدم، أغنية) من غير تاريخ لكل استماع على حدة، فمفيش
    طريقة نستخرج بيها "استمعيت كام مرة في 2026" تحديدًا - الأرقام هنا
    تراكمية من أول ما المستخدم بدأ يستخدم الموقع.

    Public (like public_profile) and scoped to the username in the URL,
    not request.user - a link shared with someone else has to show the
    sharer's own recap when THEY open it, not whatever recap happens to
    match their own logged-in session.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    recap_user = get_object_or_404(User, username=username)

    totals = UserSongPlay.objects.filter(user=recap_user).aggregate(
        total_plays=Sum('play_count'), total_full_listens=Sum('full_listen_count'),
    )

    top_plays = list(
        UserSongPlay.objects.filter(user=recap_user, play_count__gt=0)
        .select_related('song', 'song__album').order_by('-play_count')[:5]
    )

    top_song = top_plays[0].song if top_plays else None

    total_likes = Like.objects.filter(user=recap_user).count()
    total_duets = SingWithTamerProject.objects.filter(user=recap_user, is_completed=True).count()

    game_profile = UserGameProfile.objects.filter(user=recap_user).first()
    game_rank, game_rank_trend = get_rank_and_trend(game_profile) if game_profile else (None, None)

    return render(request, 'website/pages/user/recap.html', {
        'recap_user': recap_user,
        'total_plays': totals['total_plays'] or 0,
        'total_full_listens': totals['total_full_listens'] or 0,
        'top_plays': top_plays,
        'top_song': top_song,
        'total_likes': total_likes,
        'total_duets': total_duets,
        'member_since': recap_user.date_joined,
        'game_profile': game_profile,
        'game_rank': game_rank,
        'game_rank_trend': game_rank_trend,
    })


@login_required
def recently_played(request):
    """عرض الأغاني التي استمعها المستخدم مؤخراً"""
    user_plays = UserSongPlay.objects.filter(
        user=request.user
    ).select_related('song').order_by('-last_played_at')
    
    songs = [play.song for play in user_plays]
    
    return render(request, 'website/pages/user/recently_played.html', {
        'songs': songs,
    })
