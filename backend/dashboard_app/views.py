import json
from datetime import timedelta
from urllib.parse import urlencode

from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.db.models import Count, Max, Q
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _

from backend.analytics_app.models import AnalyticsEvent
from backend.concerts_app.models import Concert
from backend.dashboard_app.forms import (
    AlbumForm, ConcertForm, MediaForm, PersonForm, PlatformForm, SongForm, SongLyricSegmentForm, StudioForm,
    UserAccountForm,
)
from backend.links_app.models import Platform
from backend.main_app.models import UserAccount
from backend.media_app.models import Media
from backend.music_app.models import Album, Song, SongLyricSegment
from backend.people_app.models import Person
from backend.studios_app.models import Studio

PAGE_SIZE = 20


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def dashboard_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard_app:home')

    error = None
    if request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST.get('username'),
            password=request.POST.get('password'),
        )
        if user and user.is_active and user.role in UserAccount.DASHBOARD_ROLES:
            auth_login(request, user)
            return redirect('dashboard_app:home')
        error = 'اسم المستخدم أو كلمة المرور غير صحيحة.'

    return render(request, 'dashboard/login.html', {'error': error})


@login_required(login_url='dashboard_app:login')
def dashboard_logout(request):
    auth_logout(request)
    return redirect('dashboard_app:login')


@login_required(login_url='dashboard_app:login')
def home(request):
    stats = {
        'people': Person.objects.count(),
        'studios': Studio.objects.count(),
        'albums': Album.objects.count(),
        'songs': Song.objects.count(),
        'media': Media.objects.count(),
        'concerts': Concert.objects.count(),
    }
    return render(request, 'dashboard/main.html', {'stats': stats})


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _save_form(request, form_class, instance, page_title, back_url, redirect_to, **form_kwargs):
    form = form_class(
        request.POST or None, request.FILES or None, instance=instance, **form_kwargs,
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect(redirect_to)
    return render(request, 'dashboard/pages/_form_generic.html', {
        'form': form, 'page_title': page_title, 'back_url': _smart_back_url(request, back_url),
    })


def _visibility_choices_display(obj):
    return obj.get_visibility_display()


def _paginate(request, queryset):
    paginator = Paginator(queryset, PAGE_SIZE)
    return paginator.get_page(request.GET.get('page'))


def _querystring(request):
    """Current GET params (minus 'page') as a URL-encoded prefix, for
    pagination links that need to preserve an active search/filter.
    """
    params = {k: v for k, v in request.GET.items() if k != 'page' and v}
    return urlencode(params) + '&' if params else ''


def _smart_back_url(request, fallback):
    """Return wherever the user actually came from (e.g. Tamer's profile
    page when they clicked into one of his songs), falling back to the
    entity's list page when there's no usable referer.
    """
    referer = request.META.get('HTTP_REFERER')
    if referer and url_has_allowed_host_and_scheme(
        referer, allowed_hosts={request.get_host()}, require_https=request.is_secure(),
    ):
        return referer
    return fallback


def _event_counts_for(instance):
    """View/play/share/click totals for one object, for display on its
    own dashboard detail page.
    """
    ct = ContentType.objects.get_for_model(instance)
    counts = dict.fromkeys(AnalyticsEvent.EventType.values, 0)
    for row in (
        AnalyticsEvent.objects.filter(content_type=ct, object_id=instance.pk)
        .values('event_type').annotate(total=Count('id'))
    ):
        counts[row['event_type']] = row['total']
    return counts


def _top_viewed(model, name_field, url_name, limit=10):
    ct = ContentType.objects.get_for_model(model)
    ranked = (
        AnalyticsEvent.objects.filter(event_type=AnalyticsEvent.EventType.VIEW, content_type=ct)
        .values('object_id').annotate(views=Count('id')).order_by('-views')[:limit]
    )
    views_by_id = {row['object_id']: row['views'] for row in ranked}
    if not views_by_id:
        return []
    objects = {obj.pk: obj for obj in model.objects.filter(pk__in=views_by_id.keys())}
    ordered_ids = sorted(views_by_id, key=lambda pk: views_by_id[pk], reverse=True)
    return [
        {
            'label': getattr(objects[pk], name_field),
            'views': views_by_id[pk],
            'url': reverse(url_name, args=[pk]),
        }
        for pk in ordered_ids if pk in objects
    ]


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

@login_required(login_url='dashboard_app:login')
def analytics_overview(request):
    now = timezone.now()
    last_30_days = now - timedelta(days=30)

    totals_all_time = dict.fromkeys(AnalyticsEvent.EventType.values, 0)
    for row in AnalyticsEvent.objects.values('event_type').annotate(total=Count('id')):
        totals_all_time[row['event_type']] = row['total']

    totals_30d = dict.fromkeys(AnalyticsEvent.EventType.values, 0)
    for row in (
        AnalyticsEvent.objects.filter(created_at__gte=last_30_days)
        .values('event_type').annotate(total=Count('id'))
    ):
        totals_30d[row['event_type']] = row['total']

    platform_breakdown = list(
        AnalyticsEvent.objects.filter(event_type=AnalyticsEvent.EventType.EXTERNAL_CLICK, platform__isnull=False)
        .values('platform__platform_name').annotate(total=Count('id')).order_by('-total')
    )
    share_breakdown = list(
        AnalyticsEvent.objects.filter(event_type=AnalyticsEvent.EventType.SHARE)
        .values('share_channel').annotate(total=Count('id')).order_by('-total')
    )

    daily_views = (
        AnalyticsEvent.objects.filter(event_type=AnalyticsEvent.EventType.VIEW, created_at__gte=last_30_days)
        .annotate(day=TruncDate('created_at')).values('day').annotate(total=Count('id')).order_by('day')
    )
    daily_views_labels = json.dumps([row['day'].strftime('%Y-%m-%d') for row in daily_views])
    daily_views_data = json.dumps([row['total'] for row in daily_views])

    top_people = _top_viewed(Person, 'full_name_ar', 'dashboard_app:person-view')
    top_songs = _top_viewed(Song, 'title_ar', 'dashboard_app:song-view')
    top_media = _top_viewed(Media, 'title_ar', 'dashboard_app:media-view')
    top_albums = _top_viewed(Album, 'title_ar', 'dashboard_app:album-view')
    top_concerts = _top_viewed(Concert, 'title_ar', 'dashboard_app:concert-view')

    return render(request, 'dashboard/pages/analytics.html', {
        'totals_all_time': totals_all_time,
        'totals_30d': totals_30d,
        'platform_breakdown': platform_breakdown,
        'share_breakdown': share_breakdown,
        'daily_views_labels': daily_views_labels,
        'daily_views_data': daily_views_data,
        'top_people': top_people,
        'top_songs': top_songs,
        'top_media': top_media,
        'top_albums': top_albums,
        'top_concerts': top_concerts,
    })


# ---------------------------------------------------------------------------
# People
# ---------------------------------------------------------------------------

@login_required(login_url='dashboard_app:login')
def people_list(request):
    queryset = Person.objects.all()
    q = request.GET.get('q')
    if q:
        queryset = queryset.filter(Q(full_name_ar__icontains=q) | Q(full_name_en__icontains=q))
    role_filter = request.GET.get('filter')
    if role_filter:
        queryset = queryset.filter(primary_role=role_filter)
    people = _paginate(request, queryset)
    return render(request, 'dashboard/pages/people/all.html', {
        'people': people,
        'filter_choices': Person.Role.choices,
        'filter_label': _('كل الأدوار'),
        'querystring': _querystring(request),
    })


@login_required(login_url='dashboard_app:login')
def person_create(request):
    return _save_form(
        request, PersonForm, None, _('إضافة فنان / عضو طاقم'), reverse('dashboard_app:people'),
        'dashboard_app:people',
    )


@login_required(login_url='dashboard_app:login')
def person_edit(request, pk):
    person = get_object_or_404(Person, pk=pk)
    return _save_form(
        request, PersonForm, person, f'{_("تعديل")}: {person}', reverse('dashboard_app:people'),
        'dashboard_app:people',
    )


@login_required(login_url='dashboard_app:login')
def person_view(request, pk):
    person = get_object_or_404(Person, pk=pk)
    fields = [
        (_('الاسم بالعربية'), person.full_name_ar),
        (_('الاسم بالإنجليزية'), person.full_name_en),
        (_('نبذة'), person.bio),
    ]

    song_credits = person.song_credits.select_related('song', 'song__album').order_by('-song__release_year')
    media_credits = person.media_credits.select_related('media').order_by('-media__release_date')

    albums = {}
    for credit in song_credits:
        if credit.song.album_id and credit.song.album_id not in albums:
            albums[credit.song.album_id] = credit.song.album

    related_sections = [
        {
            'title': _('الألبومات'),
            'items': [
                {'label': album.title_ar, 'url': reverse('dashboard_app:album-view', args=[album.pk])}
                for album in albums.values()
            ],
        },
        {
            'title': _('الأغاني'),
            'items': [
                {
                    'label': credit.song.title_ar,
                    'url': reverse('dashboard_app:song-view', args=[credit.song_id]),
                    'meta': credit.get_role_display(),
                }
                for credit in song_credits
            ],
        },
        {
            'title': _('الأفلام والمسلسلات والإعلانات'),
            'items': [
                {
                    'label': credit.media.title_ar,
                    'url': reverse('dashboard_app:media-view', args=[credit.media_id]),
                    'meta': (
                        f'{credit.get_role_display()} ({credit.character_name})'
                        if credit.character_name else credit.get_role_display()
                    ),
                }
                for credit in media_credits
            ],
        },
    ]

    return render(request, 'dashboard/pages/_detail_generic.html', {
        'page_title': person.full_name_ar,
        'subtitle': person.get_primary_role_display(),
        'fields': fields,
        'related_sections': related_sections,
        'image_url': person.profile_image.url if person.profile_image else None,
        'stats': _event_counts_for(person),
        'edit_url': reverse('dashboard_app:person-edit', args=[pk]),
        'back_url': _smart_back_url(request, reverse('dashboard_app:people')),
    })


@login_required(login_url='dashboard_app:login')
def person_delete(request, pk):
    person = get_object_or_404(Person, pk=pk)
    if request.method == 'POST':
        person.delete()
    return redirect('dashboard_app:people')


# ---------------------------------------------------------------------------
# Studios
# ---------------------------------------------------------------------------

@login_required(login_url='dashboard_app:login')
def studios_list(request):
    queryset = Studio.objects.all()
    q = request.GET.get('q')
    if q:
        queryset = queryset.filter(name__icontains=q)
    type_filter = request.GET.get('filter')
    if type_filter:
        queryset = queryset.filter(entity_type=type_filter)
    studios = _paginate(request, queryset)
    return render(request, 'dashboard/pages/studios/all.html', {
        'studios': studios,
        'filter_choices': Studio.EntityType.choices,
        'filter_label': _('كل الأنواع'),
        'querystring': _querystring(request),
    })


@login_required(login_url='dashboard_app:login')
def studio_create(request):
    return _save_form(
        request, StudioForm, None, _('إضافة استوديو / شركة'), reverse('dashboard_app:studios'),
        'dashboard_app:studios',
    )


@login_required(login_url='dashboard_app:login')
def studio_edit(request, pk):
    studio = get_object_or_404(Studio, pk=pk)
    return _save_form(
        request, StudioForm, studio, f'{_("تعديل")}: {studio.name}', reverse('dashboard_app:studios'),
        'dashboard_app:studios',
    )


@login_required(login_url='dashboard_app:login')
def studio_view(request, pk):
    studio = get_object_or_404(Studio, pk=pk)
    fields = [(_('الاسم'), studio.name)]

    related_sections = [
        {
            'title': _('الألبومات'),
            'items': [
                {'label': album.title_ar, 'url': reverse('dashboard_app:album-view', args=[album.pk])}
                for album in studio.albums.all()
            ],
        },
        {
            'title': _('الأغاني المسجلة في هذا الاستوديو'),
            'items': [
                {'label': song.title_ar, 'url': reverse('dashboard_app:song-view', args=[song.pk])}
                for song in studio.recorded_songs.all()
            ],
        },
        {
            'title': _('الحفلات المنظمة'),
            'items': [
                {'label': concert.title_ar, 'url': reverse('dashboard_app:concert-view', args=[concert.pk])}
                for concert in studio.organized_concerts.all()
            ],
        },
    ]

    return render(request, 'dashboard/pages/_detail_generic.html', {
        'page_title': studio.name,
        'subtitle': studio.get_entity_type_display(),
        'fields': fields,
        'related_sections': related_sections,
        'image_url': studio.logo.url if studio.logo else None,
        'stats': _event_counts_for(studio),
        'edit_url': reverse('dashboard_app:studio-edit', args=[pk]),
        'back_url': _smart_back_url(request, reverse('dashboard_app:studios')),
    })


@login_required(login_url='dashboard_app:login')
def studio_delete(request, pk):
    studio = get_object_or_404(Studio, pk=pk)
    if request.method == 'POST':
        studio.delete()
    return redirect('dashboard_app:studios')


# ---------------------------------------------------------------------------
# Albums
# ---------------------------------------------------------------------------

@login_required(login_url='dashboard_app:login')
def albums_list(request):
    queryset = Album.objects.select_related('record_label')
    q = request.GET.get('q')
    if q:
        queryset = queryset.filter(Q(title_ar__icontains=q) | Q(title_en__icontains=q))
    visibility_filter = request.GET.get('filter')
    if visibility_filter:
        queryset = queryset.filter(visibility=visibility_filter)
    albums = _paginate(request, queryset)
    return render(request, 'dashboard/pages/albums/all.html', {
        'albums': albums,
        'filter_choices': Album.Visibility.choices,
        'filter_label': _('كل الحالات'),
        'querystring': _querystring(request),
    })


@login_required(login_url='dashboard_app:login')
def album_create(request):
    return _save_form(
        request, AlbumForm, None, _('إضافة ألبوم'), reverse('dashboard_app:albums'),
        'dashboard_app:albums',
    )


@login_required(login_url='dashboard_app:login')
def album_edit(request, pk):
    album = get_object_or_404(Album, pk=pk)
    return _save_form(
        request, AlbumForm, album, f'{_("تعديل")}: {album.title_ar}', reverse('dashboard_app:albums'),
        'dashboard_app:albums',
    )


@login_required(login_url='dashboard_app:login')
def album_view(request, pk):
    album = get_object_or_404(Album, pk=pk)
    fields = [
        (_('العنوان بالعربية'), album.title_ar),
        (_('العنوان بالإنجليزية'), album.title_en),
        (_('تاريخ الإصدار'), album.release_date),
        (_('شركة الإنتاج'), album.record_label.name if album.record_label else None),
        (_('حالة الظهور'), _visibility_choices_display(album)),
        (_('موعد النشر'), album.publish_at),
    ]

    related_sections = [
        {
            'title': _('الأغاني'),
            'items': [
                {
                    'label': song.title_ar,
                    'url': reverse('dashboard_app:song-view', args=[song.pk]),
                    'meta': song.get_song_type_display(),
                }
                for song in album.songs.all()
            ],
        },
    ]

    return render(request, 'dashboard/pages/_detail_generic.html', {
        'page_title': album.title_ar,
        'subtitle': album.release_date,
        'fields': fields,
        'related_sections': related_sections,
        'image_url': album.cover_art_url or None,
        'stats': _event_counts_for(album),
        'edit_url': reverse('dashboard_app:album-edit', args=[pk]),
        'back_url': _smart_back_url(request, reverse('dashboard_app:albums')),
    })


@login_required(login_url='dashboard_app:login')
def album_delete(request, pk):
    album = get_object_or_404(Album, pk=pk)
    if request.method == 'POST':
        album.delete()
    return redirect('dashboard_app:albums')


@login_required(login_url='dashboard_app:login')
def album_toggle_visibility(request, pk):
    album = get_object_or_404(Album, pk=pk)
    if request.method == 'POST':
        album.visibility = (
            Album.Visibility.DRAFT if album.visibility != Album.Visibility.DRAFT else Album.Visibility.PUBLISHED
        )
        album.save(update_fields=['visibility'])
    return redirect('dashboard_app:albums')


# ---------------------------------------------------------------------------
# Songs
# ---------------------------------------------------------------------------

@login_required(login_url='dashboard_app:login')
def songs_list(request):
    queryset = Song.objects.select_related('album', 'recording_studio', 'related_media')
    q = request.GET.get('q')
    if q:
        queryset = queryset.filter(Q(title_ar__icontains=q) | Q(title_en__icontains=q))
    type_filter = request.GET.get('filter')
    if type_filter:
        queryset = queryset.filter(song_type=type_filter)
    songs = _paginate(request, queryset)
    return render(request, 'dashboard/pages/songs/all.html', {
        'songs': songs,
        'filter_choices': Song.SongType.choices,
        'filter_label': _('كل الأنواع'),
        'querystring': _querystring(request),
    })


@login_required(login_url='dashboard_app:login')
def song_create(request):
    return _save_form(
        request, SongForm, None, _('إضافة أغنية'), reverse('dashboard_app:songs'),
        'dashboard_app:songs',
    )


@login_required(login_url='dashboard_app:login')
def song_edit(request, pk):
    song = get_object_or_404(Song, pk=pk)
    return _save_form(
        request, SongForm, song, f'{_("تعديل")}: {song.title_ar}', reverse('dashboard_app:songs'),
        'dashboard_app:songs',
    )


@login_required(login_url='dashboard_app:login')
def song_view(request, pk):
    song = get_object_or_404(
        Song.objects.select_related('album', 'related_media', 'recording_studio'), pk=pk,
    )
    fields = [
        (_('العنوان بالعربية'), song.title_ar),
        (_('العنوان بالإنجليزية'), song.title_en),
        (_('النوع'), song.get_song_type_display()),
        (_('الألبوم'), song.album.title_ar if song.album else None),
        (_('العمل المرتبط'), song.related_media.title_ar if song.related_media else None),
        (_('استوديو التسجيل'), song.recording_studio.name if song.recording_studio else None),
        (_('سنة الإصدار'), song.release_year),
        (_('المدة (ثانية)'), song.duration_seconds),
        (_('دويتو'), _('نعم') if song.is_duet else _('لا')),
        (_('حالة الظهور'), _visibility_choices_display(song)),
        (_('موعد النشر'), song.publish_at),
        (_('الكلمات'), song.lyrics),
    ]

    related_sections = [
        {
            'title': _('المشاركون في الأغنية'),
            'items': [
                {
                    'label': credit.person.full_name_ar,
                    'url': reverse('dashboard_app:person-view', args=[credit.person_id]),
                    'meta': credit.get_role_display(),
                }
                for credit in song.credits.select_related('person').all()
            ],
        },
        {
            'title': _('روابط الاستماع والمشاهدة'),
            'items': [
                {
                    'label': link.platform.get_platform_name_display(),
                    'url': link.direct_url,
                    'meta': link.get_access_type_display(),
                    'external': True,
                }
                for link in song.links.select_related('platform').all()
            ],
        },
        {
            'title': _('توقيت الكلمات (المقاطع)'),
            'items': [
                {
                    'label': segment.text if segment.text else segment.get_segment_type_display(),
                    'url': reverse('dashboard_app:song-segment-edit', args=[pk, segment.pk]),
                    'meta': f'{segment.start_seconds}s – {segment.end_seconds}s',
                }
                for segment in song.lyric_segments.all()
            ],
        },
    ]

    image_url = None
    if song.cover_image:
        image_url = song.cover_image.url
    elif song.album and song.album.cover_art_url:
        image_url = song.album.cover_art_url

    return render(request, 'dashboard/pages/_detail_generic.html', {
        'page_title': song.title_ar,
        'subtitle': song.get_song_type_display(),
        'fields': fields,
        'related_sections': related_sections,
        'image_url': image_url,
        'stats': _event_counts_for(song),
        'extra_actions': [
            {'label': _('إدارة توقيت الكلمات'), 'url': reverse('dashboard_app:song-segments', args=[pk])},
        ],
        'edit_url': reverse('dashboard_app:song-edit', args=[pk]),
        'back_url': _smart_back_url(request, reverse('dashboard_app:songs')),
    })


@login_required(login_url='dashboard_app:login')
def song_delete(request, pk):
    song = get_object_or_404(Song, pk=pk)
    if request.method == 'POST':
        song.delete()
    return redirect('dashboard_app:songs')


@login_required(login_url='dashboard_app:login')
def song_toggle_visibility(request, pk):
    song = get_object_or_404(Song, pk=pk)
    if request.method == 'POST':
        song.visibility = (
            Song.Visibility.DRAFT if song.visibility != Song.Visibility.DRAFT else Song.Visibility.PUBLISHED
        )
        song.save(update_fields=['visibility'])
    return redirect('dashboard_app:songs')


@login_required(login_url='dashboard_app:login')
def song_segments(request, pk):
    song = get_object_or_404(Song, pk=pk)
    segments = song.lyric_segments.all()
    last_end = segments.aggregate(Max('end_seconds'))['end_seconds__max']

    if request.method == 'POST':
        form = SongLyricSegmentForm(request.POST)
        if form.is_valid():
            segment = form.save(commit=False)
            segment.song = song
            segment.save()
            return redirect('dashboard_app:song-segments', pk=pk)
    else:
        form = SongLyricSegmentForm(initial={'start_seconds': last_end or 0})

    return render(request, 'dashboard/pages/songs/segments.html', {
        'song': song,
        'segments': segments,
        'form': form,
        'back_url': _smart_back_url(request, reverse('dashboard_app:song-view', args=[pk])),
    })


@login_required(login_url='dashboard_app:login')
def song_segment_edit(request, pk, segment_pk):
    song = get_object_or_404(Song, pk=pk)
    segment = get_object_or_404(SongLyricSegment, pk=segment_pk, song=song)
    form = SongLyricSegmentForm(request.POST or None, instance=segment)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('dashboard_app:song-segments', pk=song.pk)
    return render(request, 'dashboard/pages/_form_generic.html', {
        'form': form,
        'page_title': f'{_("تعديل مقطع")}: {song.title_ar}',
        'back_url': _smart_back_url(request, reverse('dashboard_app:song-segments', args=[song.pk])),
    })


@login_required(login_url='dashboard_app:login')
def song_segment_delete(request, pk, segment_pk):
    segment = get_object_or_404(SongLyricSegment, pk=segment_pk, song_id=pk)
    if request.method == 'POST':
        segment.delete()
    return redirect('dashboard_app:song-segments', pk=pk)


# ---------------------------------------------------------------------------
# Media (movies / series / commercials / programs)
# ---------------------------------------------------------------------------

@login_required(login_url='dashboard_app:login')
def media_list(request):
    queryset = Media.objects.all()
    q = request.GET.get('q')
    if q:
        queryset = queryset.filter(Q(title_ar__icontains=q) | Q(title_en__icontains=q))
    type_filter = request.GET.get('filter')
    if type_filter:
        queryset = queryset.filter(media_type=type_filter)
    media_items = _paginate(request, queryset)
    return render(request, 'dashboard/pages/media/all.html', {
        'media_items': media_items,
        'filter_choices': Media.MediaType.choices,
        'filter_label': _('كل الأنواع'),
        'querystring': _querystring(request),
    })


@login_required(login_url='dashboard_app:login')
def media_create(request):
    return _save_form(
        request, MediaForm, None, _('إضافة عمل فني'), reverse('dashboard_app:media'),
        'dashboard_app:media',
    )


@login_required(login_url='dashboard_app:login')
def media_edit(request, pk):
    media = get_object_or_404(Media, pk=pk)
    return _save_form(
        request, MediaForm, media, f'{_("تعديل")}: {media.title_ar}', reverse('dashboard_app:media'),
        'dashboard_app:media',
    )


@login_required(login_url='dashboard_app:login')
def media_view(request, pk):
    media = get_object_or_404(Media, pk=pk)
    fields = [
        (_('العنوان بالعربية'), media.title_ar),
        (_('العنوان بالإنجليزية'), media.title_en),
        (_('تاريخ الإصدار'), media.release_date),
        (_('التقييم'), media.rating),
        (_('جهة الإعلان'), media.advertiser_company),
        (_('اسم العلامة التجارية'), media.brand_name),
        (_('فكرة الحملة'), media.campaign_concept),
        (_('حالة الظهور'), _visibility_choices_display(media)),
        (_('موعد النشر'), media.publish_at),
        (_('القصة'), media.synopsis),
    ]

    related_sections = [
        {
            'title': _('طاقم العمل والتمثيل'),
            'items': [
                {
                    'label': credit.person.full_name_ar,
                    'url': reverse('dashboard_app:person-view', args=[credit.person_id]),
                    'meta': (
                        f'{credit.get_role_display()} ({credit.character_name})'
                        if credit.character_name else credit.get_role_display()
                    ),
                }
                for credit in media.credits.select_related('person').all()
            ],
        },
        {
            'title': _('الأغاني المرتبطة'),
            'items': [
                {'label': song.title_ar, 'url': reverse('dashboard_app:song-view', args=[song.pk])}
                for song in media.theme_songs.all()
            ],
        },
        {
            'title': _('روابط المشاهدة'),
            'items': [
                {
                    'label': link.platform.get_platform_name_display(),
                    'url': link.direct_url,
                    'meta': link.get_access_type_display(),
                    'external': True,
                }
                for link in media.links.select_related('platform').all()
            ],
        },
    ]

    return render(request, 'dashboard/pages/_detail_generic.html', {
        'page_title': media.title_ar,
        'subtitle': media.get_media_type_display(),
        'fields': fields,
        'related_sections': related_sections,
        'image_url': media.poster_url or None,
        'stats': _event_counts_for(media),
        'edit_url': reverse('dashboard_app:media-edit', args=[pk]),
        'back_url': _smart_back_url(request, reverse('dashboard_app:media')),
    })


@login_required(login_url='dashboard_app:login')
def media_delete(request, pk):
    media = get_object_or_404(Media, pk=pk)
    if request.method == 'POST':
        media.delete()
    return redirect('dashboard_app:media')


@login_required(login_url='dashboard_app:login')
def media_toggle_visibility(request, pk):
    media = get_object_or_404(Media, pk=pk)
    if request.method == 'POST':
        media.visibility = (
            Media.Visibility.DRAFT if media.visibility != Media.Visibility.DRAFT else Media.Visibility.PUBLISHED
        )
        media.save(update_fields=['visibility'])
    return redirect('dashboard_app:media')


# ---------------------------------------------------------------------------
# Concerts
# ---------------------------------------------------------------------------

@login_required(login_url='dashboard_app:login')
def concerts_list(request):
    queryset = Concert.objects.select_related('organizer')
    q = request.GET.get('q')
    if q:
        queryset = queryset.filter(
            Q(title_ar__icontains=q) | Q(title_en__icontains=q) | Q(city__icontains=q) | Q(venue_name__icontains=q)
        )
    status_filter = request.GET.get('filter')
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    concerts = _paginate(request, queryset)
    return render(request, 'dashboard/pages/concerts/all.html', {
        'concerts': concerts,
        'filter_choices': Concert.Status.choices,
        'filter_label': _('كل الحالات'),
        'querystring': _querystring(request),
    })


@login_required(login_url='dashboard_app:login')
def concert_create(request):
    return _save_form(
        request, ConcertForm, None, _('إضافة حفلة'), reverse('dashboard_app:concerts'),
        'dashboard_app:concerts',
    )


@login_required(login_url='dashboard_app:login')
def concert_edit(request, pk):
    concert = get_object_or_404(Concert, pk=pk)
    return _save_form(
        request, ConcertForm, concert, f'{_("تعديل")}: {concert.title_ar}', reverse('dashboard_app:concerts'),
        'dashboard_app:concerts',
    )


@login_required(login_url='dashboard_app:login')
def concert_view(request, pk):
    concert = get_object_or_404(Concert, pk=pk)
    fields = [
        (_('العنوان بالعربية'), concert.title_ar),
        (_('العنوان بالإنجليزية'), concert.title_en),
        (_('التاريخ'), concert.date),
        (_('المكان'), concert.venue_name),
        (_('المدينة'), concert.city),
        (_('الدولة'), concert.country),
        (_('الجهة المنظمة'), concert.organizer.name if concert.organizer else None),
        (_('حالة الظهور'), _visibility_choices_display(concert)),
        (_('موعد النشر'), concert.publish_at),
        (_('الوصف'), concert.description),
    ]

    related_sections = [
        {
            'title': _('الفيديوهات والروابط'),
            'items': [
                {
                    'label': link.platform.get_platform_name_display(),
                    'url': link.direct_url,
                    'meta': link.get_access_type_display(),
                    'external': True,
                }
                for link in concert.links.select_related('platform').all()
            ],
        },
    ]

    return render(request, 'dashboard/pages/_detail_generic.html', {
        'page_title': concert.title_ar,
        'subtitle': concert.get_status_display(),
        'fields': fields,
        'related_sections': related_sections,
        'image_url': concert.poster_url or None,
        'stats': _event_counts_for(concert),
        'edit_url': reverse('dashboard_app:concert-edit', args=[pk]),
        'back_url': _smart_back_url(request, reverse('dashboard_app:concerts')),
    })


@login_required(login_url='dashboard_app:login')
def concert_delete(request, pk):
    concert = get_object_or_404(Concert, pk=pk)
    if request.method == 'POST':
        concert.delete()
    return redirect('dashboard_app:concerts')


@login_required(login_url='dashboard_app:login')
def concert_toggle_visibility(request, pk):
    concert = get_object_or_404(Concert, pk=pk)
    if request.method == 'POST':
        concert.visibility = (
            Concert.Visibility.DRAFT if concert.visibility != Concert.Visibility.DRAFT
            else Concert.Visibility.PUBLISHED
        )
        concert.save(update_fields=['visibility'])
    return redirect('dashboard_app:concerts')


# ---------------------------------------------------------------------------
# Platforms
# ---------------------------------------------------------------------------

@login_required(login_url='dashboard_app:login')
def platforms_list(request):
    queryset = Platform.objects.all()
    type_filter = request.GET.get('filter')
    if type_filter:
        queryset = queryset.filter(platform_name=type_filter)
    platforms = _paginate(request, queryset)
    return render(request, 'dashboard/pages/platforms/all.html', {
        'platforms': platforms,
        'filter_choices': Platform.Name.choices,
        'filter_label': _('كل المنصات'),
        'querystring': _querystring(request),
    })


@login_required(login_url='dashboard_app:login')
def platform_create(request):
    return _save_form(
        request, PlatformForm, None, _('إضافة منصة'), reverse('dashboard_app:platforms'),
        'dashboard_app:platforms',
    )


@login_required(login_url='dashboard_app:login')
def platform_edit(request, pk):
    platform = get_object_or_404(Platform, pk=pk)
    return _save_form(
        request, PlatformForm, platform, f'{_("تعديل")}: {platform.get_platform_name_display()}',
        reverse('dashboard_app:platforms'), 'dashboard_app:platforms',
    )


@login_required(login_url='dashboard_app:login')
def platform_view(request, pk):
    platform = get_object_or_404(Platform, pk=pk)
    fields = [
        (_('المنصة'), platform.get_platform_name_display()),
        (_('رابط الأيقونة'), platform.logo_icon_url),
    ]

    related_sections = [
        {
            'title': _('الأعمال المرتبطة بهذه المنصة'),
            'items': [
                {
                    'label': f'{link.content_object} ({link.content_type.name})',
                    'url': link.direct_url,
                    'meta': link.get_access_type_display(),
                    'external': True,
                }
                for link in platform.links.select_related('content_type').all()
            ],
        },
    ]

    return render(request, 'dashboard/pages/_detail_generic.html', {
        'page_title': platform.get_platform_name_display(),
        'fields': fields,
        'related_sections': related_sections,
        'edit_url': reverse('dashboard_app:platform-edit', args=[pk]),
        'back_url': _smart_back_url(request, reverse('dashboard_app:platforms')),
    })


@login_required(login_url='dashboard_app:login')
def platform_delete(request, pk):
    platform = get_object_or_404(Platform, pk=pk)
    if request.method == 'POST':
        platform.delete()
    return redirect('dashboard_app:platforms')


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

@login_required(login_url='dashboard_app:login')
def users_list(request):
    queryset = UserAccount.objects.all()
    q = request.GET.get('q')
    if q:
        queryset = queryset.filter(Q(username__icontains=q) | Q(email__icontains=q))
    role_filter = request.GET.get('filter')
    if role_filter:
        queryset = queryset.filter(role=role_filter)
    accounts = _paginate(request, queryset)
    return render(request, 'dashboard/pages/users/all.html', {
        'accounts': accounts,
        'filter_choices': UserAccount.Role.choices,
        'filter_label': _('كل الأدوار'),
        'querystring': _querystring(request),
    })


@login_required(login_url='dashboard_app:login')
def user_create(request):
    return _save_form(
        request, UserAccountForm, None, _('إضافة مستخدم'), reverse('dashboard_app:users'),
        'dashboard_app:users',
    )


@login_required(login_url='dashboard_app:login')
def user_edit(request, pk):
    account = get_object_or_404(UserAccount, pk=pk)
    return _save_form(
        request, UserAccountForm, account, f'{_("تعديل")}: {account.username}', reverse('dashboard_app:users'),
        'dashboard_app:users',
    )


@login_required(login_url='dashboard_app:login')
def user_view(request, pk):
    account = get_object_or_404(UserAccount, pk=pk)
    fields = [
        (_('اسم المستخدم'), account.username),
        (_('البريد الإلكتروني'), account.email),
        (_('الحالة'), _('مفعّل') if account.is_active else _('موقوف')),
    ]
    return render(request, 'dashboard/pages/_detail_generic.html', {
        'page_title': account.username,
        'subtitle': account.get_role_display(),
        'fields': fields,
        'edit_url': reverse('dashboard_app:user-edit', args=[pk]),
        'back_url': _smart_back_url(request, reverse('dashboard_app:users')),
    })


@login_required(login_url='dashboard_app:login')
def user_delete(request, pk):
    account = get_object_or_404(UserAccount, pk=pk)
    if request.method == 'POST' and account.pk != request.user.pk:
        account.delete()
    return redirect('dashboard_app:users')


@login_required(login_url='dashboard_app:login')
def user_toggle_active(request, pk):
    account = get_object_or_404(UserAccount, pk=pk)
    if request.method == 'POST' and account.pk != request.user.pk:
        account.is_active = not account.is_active
        account.save(update_fields=['is_active'])
    return redirect('dashboard_app:users')
