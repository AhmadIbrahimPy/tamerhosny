from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from backend.ads_app.models import Advertisement
from backend.ai_remix_app.models import RemixProject, RemixSource, AudioSource
from backend.main_app.models import Like, Playlist, PlaylistItem, UserSongPlay, CurrentSongListener
from backend.main_app.shared_utils.credits import dedupe_credits
from backend.concerts_app.models import Concert
from backend.media_app.models import Media
from backend.music_app.models import Album, Song, SongCredit
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


def home(request):
    songs = Song.visible_queryset(Song.objects.select_related('album'))[:7]
    movies = Media.visible_queryset(Media.objects.filter(media_type=Media.MediaType.MOVIE))[:7]
    series = Media.visible_queryset(Media.objects.filter(media_type=Media.MediaType.TV_SERIES))[:7]
    commercials = Media.visible_queryset(Media.objects.filter(media_type=Media.MediaType.COMMERCIAL))[:7]
    albums = Album.visible_queryset(Album.objects.all())[:7]
    concerts = Concert.visible_queryset(Concert.objects.all())[:4]
    people = Person.objects.all()[:8]
    home_ads = list(_ads_for(Advertisement.Placement.HOME)[:8])
    return render(request, 'website/pages/home.html', {
        'songs': songs,
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


@csrf_exempt
def song_player_data(request):
    """API endpoint to get song data for player page."""
    try:
        song_id = request.POST.get('song_id') if request.method == 'POST' else request.GET.get('song_id')
        current_song_id = request.POST.get('current_song_id') if request.method == 'POST' else request.GET.get('current_song_id')

        if not song_id:
            return JsonResponse({'error': 'song_id required'}, status=400)

        song = Song.objects.select_related('album').get(pk=song_id)

        # Get other songs from same album
        album_songs = []
        if song.album_id:
            album_songs = list(Song.objects.select_related('album').filter(album_id=song.album_id).exclude(pk=song.pk)[:12])

        # Get credits
        all_credits = list(song.credits.select_related('person').all())
        vocal_roles = (SongCredit.Role.SINGER, SongCredit.Role.FEATURED_ARTIST)
        singers = [credit for credit in all_credits if credit.role in vocal_roles]
        crew_credits = [credit for credit in all_credits if credit.role not in vocal_roles]

        # Build response
        print(f"Song cover_image: {song.cover_image}")
        print(f"Album: {song.album}")
        if song.album:
            print(f"Album cover_image: {song.album.cover_image}")

        data = {
            'title': song.title_ar,
            'title_en': song.title_en,
            'artist': ', '.join([credit.person.full_name_ar for credit in singers]),
            'album': song.album.title_ar if song.album else '',
            'image': song.cover_image.url if song.cover_image else (song.album.cover_image.url if song.album and song.album.cover_image else ''),
            'songId': song.pk,
            'url': song.audio_file.url if song.audio_file else '',
            'currentSongId': int(current_song_id) if current_song_id else None,
            'otherSongs': [
                {
                    'title': s.title_ar,
                    'image': s.cover_image.url if s.cover_image else (s.album.cover_image.url if s.album and s.album.cover_image else ''),
                    'link': f'/songs/{s.slug}/',
                    'duration': f"{s.duration_seconds // 60}:{s.duration_seconds % 60:02d}" if s.duration_seconds else '',
                    'songId': s.pk
                }
                for s in album_songs
            ],
            'credits': [
                {
                    'personName': credit.person.full_name_ar,
                    'personSlug': credit.person.slug,
                    'personImage': credit.person.profile_image.url if credit.person.profile_image else '',
                    'role': credit.get_role_display()
                }
                for credit in crew_credits
            ],
            'platforms': []
        }

        print(f"Response data image: {data['image']}")
        print(f"First other song image: {data['otherSongs'][0]['image'] if data['otherSongs'] else 'N/A'}")

        return JsonResponse(data)

    except Song.DoesNotExist:
        return JsonResponse({'error': 'Song not found'}, status=404)
    except Exception as e:
        import traceback
        print(f"Error in song_player_data: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return JsonResponse({'error': str(e)}, status=500)


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


def song_detail(request, slug):
    song = get_object_or_404(
        Song.objects.select_related('album', 'related_media', 'recording_studio'), slug=slug,
    )
    
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

    top_ad, bottom_ad = _ad_slots(Advertisement.Placement.SONGS)
    return render(request, 'website/pages/songs/detail.html', {
        'song': song,
        'singers': singers,
        'credits': dedupe_credits(crew_credits, 'person'),
        'links': song.links.select_related('platform').all(),
        'album_songs': album_songs,
        'other_songs': other_songs,
        'top_ad': top_ad,
        'bottom_ad': bottom_ad,
        'is_liked': is_liked,
        'like_count': like_count,
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
def increment_play_count(request):
    """زيادة عدد مرات التشغيل للأغنية (فقط إذا مرت ساعة على آخر تشغيل للمستخدم)"""
    song_id = request.POST.get('song_id')
    
    if not song_id:
        return JsonResponse({'status': 'error', 'message': 'Missing song_id'}, status=400)
    
    try:
        from django.utils import timezone
        from datetime import timedelta
        
        song = Song.objects.get(pk=song_id)
        
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


@require_POST
def start_listening(request):
    """بدء الاستماع لأغنية"""
    song_id = request.POST.get('song_id')
    
    if not song_id:
        return JsonResponse({'status': 'error', 'message': 'Missing song_id'}, status=400)
    
    try:
        song = Song.objects.get(pk=song_id)
        
        # Only track logged in users
        if not request.user.is_authenticated:
            return JsonResponse({'status': 'success', 'listener_count': 0})
        
        # Create or update current listener
        listener, created = CurrentSongListener.objects.get_or_create(
            user=request.user,
            song=song
        )
        
        if not created:
            # Update heartbeat if already exists
            from django.utils import timezone
            listener.last_heartbeat = timezone.now()
            listener.save()
        
        # Get current listener count
        listener_count = CurrentSongListener.objects.filter(song=song).count()
        
        return JsonResponse({'status': 'success', 'listener_count': listener_count})
    except Song.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Song not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@require_POST
def stop_listening(request):
    """إيقاف الاستماع لأغنية"""
    song_id = request.POST.get('song_id')
    
    if not song_id:
        return JsonResponse({'status': 'error', 'message': 'Missing song_id'}, status=400)
    
    try:
        song = Song.objects.get(pk=song_id)
        
        # Only track logged in users
        if not request.user.is_authenticated:
            return JsonResponse({'status': 'success', 'listener_count': 0})
        
        # Remove current listener
        CurrentSongListener.objects.filter(
            user=request.user,
            song=song
        ).delete()
        
        # Get current listener count
        listener_count = CurrentSongListener.objects.filter(song=song).count()
        
        return JsonResponse({'status': 'success', 'listener_count': listener_count})
    except Song.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Song not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_POST
def listening_heartbeat(request):
    """تحديث نبض الاستماع (للتأكد من أن المستخدم لسه بيسمع)"""
    song_id = request.POST.get('song_id')
    
    if not song_id:
        return JsonResponse({'status': 'error', 'message': 'Missing song_id'}, status=400)
    
    try:
        from django.utils import timezone
        from datetime import timedelta
        
        song = Song.objects.get(pk=song_id)
        
        # Update heartbeat
        listener = CurrentSongListener.objects.filter(
            user=request.user,
            song=song
        ).first()
        
        if listener:
            listener.last_heartbeat = timezone.now()
            listener.save()
        else:
            # Create if doesn't exist
            CurrentSongListener.objects.create(
                user=request.user,
                song=song
            )
        
        # Clean up old listeners (no heartbeat for 2 minutes)
        from django.utils import timezone
        cutoff_time = timezone.now() - timedelta(minutes=2)
        CurrentSongListener.objects.filter(
            last_heartbeat__lt=cutoff_time
        ).delete()
        
        # Get current listener count
        listener_count = CurrentSongListener.objects.filter(song=song).count()
        
        return JsonResponse({'status': 'success', 'listener_count': listener_count})
    except Song.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Song not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def get_current_listeners(request):
    """الحصول على عدد المستخدمين الحاليين لأغنية"""
    song_id = request.GET.get('song_id')
    
    if not song_id:
        return JsonResponse({'status': 'error', 'message': 'Missing song_id'}, status=400)
    
    try:
        from django.utils import timezone
        from datetime import timedelta
        
        song = Song.objects.get(pk=song_id)
        
        # Clean up old listeners (no heartbeat for 2 minutes)
        cutoff_time = timezone.now() - timedelta(minutes=2)
        CurrentSongListener.objects.filter(
            last_heartbeat__lt=cutoff_time
        ).delete()
        
        # Get current listener count
        listener_count = CurrentSongListener.objects.filter(song=song).count()
        
        return JsonResponse({'status': 'success', 'listener_count': listener_count})
    except Song.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Song not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


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
            return JsonResponse({'status': 'success', 'liked': False})
        else:
            # إذا لم يكن موجوداً، تم إنشاؤه
            return JsonResponse({'status': 'success', 'liked': True})
            
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
def recently_played(request):
    """عرض الأغاني التي استمعها المستخدم مؤخراً"""
    user_plays = UserSongPlay.objects.filter(
        user=request.user
    ).select_related('song').order_by('-last_played_at')
    
    songs = [play.song for play in user_plays]
    
    return render(request, 'website/pages/user/recently_played.html', {
        'songs': songs,
    })
