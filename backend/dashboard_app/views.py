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
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _

from backend.ads_app.models import Advertisement
from backend.analytics_app.models import AnalyticsEvent
from backend.concerts_app.models import Concert
from backend.main_app.shared_utils.credits import dedupe_credits
from backend.dashboard_app.forms import (
    AdvertisementForm, AlbumForm, CinemaVenueForm, ConcertForm, ExternalLinkForm, MediaCreditForm,
    MEDIA_SECTION_FORMS, PersonForm, PlatformForm, ScreeningForm, SongCreditForm, SongForm, SongLyricSegmentForm,
    StudioForm, UserAccountForm,
)
from backend.links_app.models import ExternalLink, Platform
from backend.main_app.models import UserAccount
from backend.media_app.models import CinemaScreening, CinemaVenue, Media, MediaCredit
from backend.music_app.models import Album, Song, SongCredit, SongLyricSegment
from backend.people_app.models import Person
from backend.studios_app.models import Studio

# kind -> (Model, display-name field, list url name, detail url name)
LINKABLE_KINDS = {
    'person': (Person, 'full_name_ar', 'dashboard_app:people', 'dashboard_app:person-view'),
    'album': (Album, 'title_ar', 'dashboard_app:albums', 'dashboard_app:album-view'),
    'song': (Song, 'title_ar', 'dashboard_app:songs', 'dashboard_app:song-view'),
    'media': (Media, 'title_ar', 'dashboard_app:movies', 'dashboard_app:media-view'),
    'concert': (Concert, 'title_ar', 'dashboard_app:concerts', 'dashboard_app:concert-view'),
}

# dashboard "section" key -> (MediaType value, Arabic label, list url name).
# Movies, series and commercials are kept as fully separate browse/create
# flows even though they share one underlying Media table.
MEDIA_SECTIONS = {
    'movies': (Media.MediaType.MOVIE, _('الأفلام'), 'dashboard_app:movies'),
    'series': (Media.MediaType.TV_SERIES, _('المسلسلات'), 'dashboard_app:series'),
    'commercials': (Media.MediaType.COMMERCIAL, _('الإعلانات والحملات الترويجية'), 'dashboard_app:commercials'),
    'programs': (Media.MediaType.PROGRAM, _('البرامج'), 'dashboard_app:programs'),
}

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
# Platform links (generic: person / album / song / media / concert)
# ---------------------------------------------------------------------------

@login_required(login_url='dashboard_app:login')
def entity_links(request, kind, object_id):
    mapping = LINKABLE_KINDS.get(kind)
    if not mapping:
        return redirect('dashboard_app:home')
    model, name_field, list_url_name, detail_url_name = mapping
    instance = get_object_or_404(model, pk=object_id)
    links = ExternalLink.objects.filter(
        content_type__model=model._meta.model_name, object_id=object_id,
    ).select_related('platform')

    if request.method == 'POST':
        form = ExternalLinkForm(request.POST)
        if form.is_valid():
            link = form.save(commit=False)
            link.content_object = instance
            link.save()
            return redirect('dashboard_app:entity-links', kind=kind, object_id=object_id)
    else:
        form = ExternalLinkForm()

    return render(request, 'dashboard/pages/links_manage.html', {
        'kind': kind,
        'instance': instance,
        'instance_label': getattr(instance, name_field),
        'links': links,
        'form': form,
        'back_url': _smart_back_url(request, reverse(detail_url_name, args=[object_id])),
    })


@login_required(login_url='dashboard_app:login')
def entity_link_edit(request, kind, object_id, link_pk):
    mapping = LINKABLE_KINDS.get(kind)
    if not mapping:
        return redirect('dashboard_app:home')
    model = mapping[0]
    link = get_object_or_404(
        ExternalLink, pk=link_pk, content_type__model=model._meta.model_name, object_id=object_id,
    )
    form = ExternalLinkForm(request.POST or None, instance=link)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('dashboard_app:entity-links', kind=kind, object_id=object_id)
    return render(request, 'dashboard/pages/_form_generic.html', {
        'form': form,
        'page_title': _('تعديل رابط'),
        'back_url': _smart_back_url(request, reverse('dashboard_app:entity-links', args=[kind, object_id])),
    })


@login_required(login_url='dashboard_app:login')
def entity_link_delete(request, kind, object_id, link_pk):
    mapping = LINKABLE_KINDS.get(kind)
    if not mapping:
        return redirect('dashboard_app:home')
    model = mapping[0]
    link = get_object_or_404(
        ExternalLink, pk=link_pk, content_type__model=model._meta.model_name, object_id=object_id,
    )
    if request.method == 'POST':
        link.delete()
    return redirect('dashboard_app:entity-links', kind=kind, object_id=object_id)


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

    song_credits_qs = person.song_credits.select_related('song', 'song__album').order_by('-song__release_year')
    media_credits_qs = person.media_credits.select_related('media').order_by('-media__release_date')
    song_credits = dedupe_credits(song_credits_qs, 'song')
    media_credits = dedupe_credits(media_credits_qs, 'media', extra_label=lambda credit: credit.character_name)

    albums = {}
    for credit in song_credits_qs:
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
                    'label': entry['song'].title_ar,
                    'url': reverse('dashboard_app:song-view', args=[entry['song'].pk]),
                    'meta': '، '.join(entry['roles']),
                }
                for entry in song_credits
            ],
        },
        {
            'title': _('الأفلام والمسلسلات والإعلانات'),
            'items': [
                {
                    'label': entry['media'].title_ar,
                    'url': reverse('dashboard_app:media-view', args=[entry['media'].pk]),
                    'meta': '، '.join(entry['roles']),
                }
                for entry in media_credits
            ],
        },
        {
            'title': _('روابط المنصات'),
            'items': [
                {
                    'label': link.platform.get_platform_name_display(),
                    'url': link.direct_url,
                    'meta': link.get_access_type_display(),
                    'external': True,
                }
                for link in person.links.select_related('platform').all()
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
        'extra_actions': [
            {'label': _('روابط المنصات'), 'url': reverse('dashboard_app:entity-links', args=['person', pk])},
        ],
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
        {
            'title': _('روابط المنصات'),
            'items': [
                {
                    'label': link.platform.get_platform_name_display(),
                    'url': link.direct_url,
                    'meta': link.get_access_type_display(),
                    'external': True,
                }
                for link in album.links.select_related('platform').all()
            ],
        },
    ]

    return render(request, 'dashboard/pages/_detail_generic.html', {
        'page_title': album.title_ar,
        'subtitle': album.release_date,
        'fields': fields,
        'related_sections': related_sections,
        'image_url': (album.cover_image.url if album.cover_image else None) or album.cover_art_url or None,
        'stats': _event_counts_for(album),
        'extra_actions': [
            {'label': _('روابط المنصات'), 'url': reverse('dashboard_app:entity-links', args=['album', pk])},
        ],
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


def _album_years_json():
    return json.dumps({
        album.pk: album.release_date.year
        for album in Album.objects.exclude(release_date=None)
    })


@login_required(login_url='dashboard_app:login')
def song_create(request):
    form = SongForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        song = form.save()
        return redirect('dashboard_app:song-view', pk=song.pk)
    return render(request, 'dashboard/pages/_form_generic.html', {
        'form': form,
        'page_title': _('إضافة أغنية'),
        'back_url': _smart_back_url(request, reverse('dashboard_app:songs')),
        'album_years_json': _album_years_json(),
    })


@login_required(login_url='dashboard_app:login')
def song_edit(request, pk):
    song = get_object_or_404(Song, pk=pk)
    form = SongForm(request.POST or None, request.FILES or None, instance=song)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('dashboard_app:songs')
    return render(request, 'dashboard/pages/_form_generic.html', {
        'form': form,
        'page_title': f'{_("تعديل")}: {song.title_ar}',
        'back_url': _smart_back_url(request, reverse('dashboard_app:songs')),
        'album_years_json': _album_years_json(),
    })


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
    ]

    related_sections = [
        {
            'title': _('المشاركون في الأغنية'),
            'items': [
                {
                    'label': entry['person'].full_name_ar,
                    'url': reverse('dashboard_app:person-view', args=[entry['person'].pk]),
                    'meta': '، '.join(entry['roles']),
                }
                for entry in dedupe_credits(song.credits.select_related('person').all(), 'person')
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
            {'label': _('المشاركون في الأغنية'), 'url': reverse('dashboard_app:song-credits', args=[pk])},
            {'label': _('إدارة توقيت الكلمات'), 'url': reverse('dashboard_app:song-segments', args=[pk])},
            {'label': _('روابط المنصات'), 'url': reverse('dashboard_app:entity-links', args=['song', pk])},
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
def song_credits(request, pk):
    song = get_object_or_404(Song, pk=pk)
    credits_qs = song.credits.select_related('person').all()

    if request.method == 'POST':
        form = SongCreditForm(request.POST)
        if form.is_valid():
            credit = form.save(commit=False)
            credit.song = song
            credit.save()
            return redirect('dashboard_app:song-credits', pk=pk)
    else:
        form = SongCreditForm()

    return render(request, 'dashboard/pages/songs/credits.html', {
        'song': song,
        'credits': credits_qs,
        'form': form,
        'back_url': _smart_back_url(request, reverse('dashboard_app:song-view', args=[pk])),
    })


@login_required(login_url='dashboard_app:login')
def song_credit_edit(request, pk, credit_pk):
    song = get_object_or_404(Song, pk=pk)
    credit = get_object_or_404(SongCredit, pk=credit_pk, song=song)
    form = SongCreditForm(request.POST or None, instance=credit)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('dashboard_app:song-credits', pk=pk)
    return render(request, 'dashboard/pages/_form_generic.html', {
        'form': form,
        'page_title': f'{_("تعديل مشارك")}: {song.title_ar}',
        'back_url': _smart_back_url(request, reverse('dashboard_app:song-credits', args=[pk])),
    })


@login_required(login_url='dashboard_app:login')
def song_credit_delete(request, pk, credit_pk):
    credit = get_object_or_404(SongCredit, pk=credit_pk, song_id=pk)
    if request.method == 'POST':
        credit.delete()
    return redirect('dashboard_app:song-credits', pk=pk)


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

def _media_section_or_404(section):
    mapping = MEDIA_SECTIONS.get(section)
    if not mapping:
        raise Http404
    return mapping


_MEDIA_SECTION_CREATE_URLS = {
    'movies': 'dashboard_app:movie-create',
    'series': 'dashboard_app:series-create',
    'commercials': 'dashboard_app:commercial-create',
    'programs': 'dashboard_app:program-create',
}


def _media_section_list(request, section):
    media_type, label, list_url_name = _media_section_or_404(section)
    queryset = Media.objects.filter(media_type=media_type)
    q = request.GET.get('q')
    if q:
        queryset = queryset.filter(Q(title_ar__icontains=q) | Q(title_en__icontains=q))
    media_items = _paginate(request, queryset)
    return render(request, 'dashboard/pages/media/all.html', {
        'media_items': media_items,
        'section': section,
        'section_label': label,
        'create_url': reverse(_MEDIA_SECTION_CREATE_URLS[section]),
        'querystring': _querystring(request),
    })


def _media_section_create(request, section):
    _media_type, label, list_url_name = _media_section_or_404(section)
    form_class = MEDIA_SECTION_FORMS[section]
    return _save_form(
        request, form_class, None, f'{_("إضافة")}: {label}',
        reverse(list_url_name), reverse(list_url_name),
    )


@login_required(login_url='dashboard_app:login')
def movies_list(request):
    return _media_section_list(request, 'movies')


@login_required(login_url='dashboard_app:login')
def movie_create(request):
    return _media_section_create(request, 'movies')


@login_required(login_url='dashboard_app:login')
def series_list(request):
    return _media_section_list(request, 'series')


@login_required(login_url='dashboard_app:login')
def series_create(request):
    return _media_section_create(request, 'series')


@login_required(login_url='dashboard_app:login')
def commercials_list(request):
    return _media_section_list(request, 'commercials')


@login_required(login_url='dashboard_app:login')
def commercial_create(request):
    return _media_section_create(request, 'commercials')


@login_required(login_url='dashboard_app:login')
def programs_list(request):
    return _media_section_list(request, 'programs')


@login_required(login_url='dashboard_app:login')
def program_create(request):
    return _media_section_create(request, 'programs')


_MEDIA_TYPE_TO_SECTION = {media_type: section for section, (media_type, *_rest) in MEDIA_SECTIONS.items()}


@login_required(login_url='dashboard_app:login')
def media_edit(request, pk):
    media = get_object_or_404(Media, pk=pk)
    section = _MEDIA_TYPE_TO_SECTION[media.media_type]
    form_class = MEDIA_SECTION_FORMS[section]
    list_url = reverse(MEDIA_SECTIONS[section][2])
    return _save_form(
        request, form_class, media, f'{_("تعديل")}: {media.title_ar}',
        reverse('dashboard_app:media-view', args=[pk]), list_url,
    )


@login_required(login_url='dashboard_app:login')
def media_view(request, pk):
    media = get_object_or_404(Media, pk=pk)
    section = _MEDIA_TYPE_TO_SECTION[media.media_type]
    list_url = reverse(MEDIA_SECTIONS[section][2])

    fields = [
        (_('العنوان بالعربية'), media.title_ar),
        (_('العنوان بالإنجليزية'), media.title_en),
        (_('تاريخ الإصدار'), media.release_date),
        (_('حالة الظهور'), _visibility_choices_display(media)),
        (_('موعد النشر'), media.publish_at),
    ]
    if media.media_type == Media.MediaType.COMMERCIAL:
        fields += [
            (_('جهة الإعلان'), media.advertiser_company),
            (_('اسم العلامة التجارية'), media.brand_name),
            (_('فكرة الحملة'), media.campaign_concept),
        ]
    else:
        fields += [
            (_('التقييم'), media.rating),
            (_('القصة'), media.synopsis),
        ]

    related_sections = [
        {
            'title': _('الفنانون والتمثيل'),
            'items': [
                {
                    'label': entry['person'].full_name_ar,
                    'url': reverse('dashboard_app:person-view', args=[entry['person'].pk]),
                    'meta': '، '.join(entry['roles']),
                }
                for entry in dedupe_credits(
                    media.credits.select_related('person').all(), 'person',
                    extra_label=lambda credit: credit.character_name,
                )
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
        {
            'title': _('دور العرض'),
            'items': [
                {
                    'label': str(screening.venue),
                    'url': reverse('dashboard_app:media-screening-edit', args=[pk, screening.pk]),
                    'meta': f'{screening.ticket_price} ج.م' if screening.ticket_price else None,
                }
                for screening in media.screenings.select_related('venue').all()
            ],
        },
    ]

    return render(request, 'dashboard/pages/_detail_generic.html', {
        'page_title': media.title_ar,
        'subtitle': media.get_media_type_display(),
        'fields': fields,
        'related_sections': related_sections,
        'image_url': media.display_poster_url or None,
        'stats': _event_counts_for(media),
        'extra_actions': [
            {'label': _('الفنانون'), 'url': reverse('dashboard_app:media-crew', args=[pk])},
            {'label': _('دور العرض'), 'url': reverse('dashboard_app:media-screenings', args=[pk])},
            {'label': _('روابط المنصات'), 'url': reverse('dashboard_app:entity-links', args=['media', pk])},
        ],
        'edit_url': reverse('dashboard_app:media-edit', args=[pk]),
        'back_url': _smart_back_url(request, list_url),
    })


@login_required(login_url='dashboard_app:login')
def media_delete(request, pk):
    media = get_object_or_404(Media, pk=pk)
    section = _MEDIA_TYPE_TO_SECTION[media.media_type]
    if request.method == 'POST':
        media.delete()
    return redirect(MEDIA_SECTIONS[section][2])


@login_required(login_url='dashboard_app:login')
def media_toggle_visibility(request, pk):
    media = get_object_or_404(Media, pk=pk)
    section = _MEDIA_TYPE_TO_SECTION[media.media_type]
    if request.method == 'POST':
        media.visibility = (
            Media.Visibility.DRAFT if media.visibility != Media.Visibility.DRAFT else Media.Visibility.PUBLISHED
        )
        media.save(update_fields=['visibility'])
    return redirect(MEDIA_SECTIONS[section][2])


@login_required(login_url='dashboard_app:login')
def media_crew(request, pk):
    media = get_object_or_404(Media, pk=pk)
    credits_qs = media.credits.select_related('person').all()

    if request.method == 'POST':
        form = MediaCreditForm(request.POST)
        if form.is_valid():
            credit = form.save(commit=False)
            credit.media = media
            credit.save()
            return redirect('dashboard_app:media-crew', pk=pk)
    else:
        form = MediaCreditForm()

    return render(request, 'dashboard/pages/media/crew.html', {
        'media': media,
        'credits': credits_qs,
        'form': form,
        'back_url': _smart_back_url(request, reverse('dashboard_app:media-view', args=[pk])),
    })


@login_required(login_url='dashboard_app:login')
def media_crew_edit(request, pk, credit_pk):
    media = get_object_or_404(Media, pk=pk)
    credit = get_object_or_404(MediaCredit, pk=credit_pk, media=media)
    form = MediaCreditForm(request.POST or None, instance=credit)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('dashboard_app:media-crew', pk=pk)
    return render(request, 'dashboard/pages/_form_generic.html', {
        'form': form,
        'page_title': f'{_("تعديل فنان")}: {media.title_ar}',
        'back_url': _smart_back_url(request, reverse('dashboard_app:media-crew', args=[pk])),
    })


@login_required(login_url='dashboard_app:login')
def media_crew_delete(request, pk, credit_pk):
    credit = get_object_or_404(MediaCredit, pk=credit_pk, media_id=pk)
    if request.method == 'POST':
        credit.delete()
    return redirect('dashboard_app:media-crew', pk=pk)


@login_required(login_url='dashboard_app:login')
def media_screenings(request, pk):
    media = get_object_or_404(Media, pk=pk)
    screenings = media.screenings.select_related('venue').all()

    if request.method == 'POST':
        form = ScreeningForm(request.POST)
        if form.is_valid():
            screening = form.save(commit=False)
            screening.media = media
            screening.save()
            return redirect('dashboard_app:media-screenings', pk=pk)
    else:
        form = ScreeningForm()

    return render(request, 'dashboard/pages/media/screenings.html', {
        'media': media,
        'screenings': screenings,
        'form': form,
        'back_url': _smart_back_url(request, reverse('dashboard_app:media-view', args=[pk])),
    })


@login_required(login_url='dashboard_app:login')
def media_screening_edit(request, pk, screening_pk):
    media = get_object_or_404(Media, pk=pk)
    screening = get_object_or_404(CinemaScreening, pk=screening_pk, media=media)
    form = ScreeningForm(request.POST or None, instance=screening)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('dashboard_app:media-screenings', pk=pk)
    return render(request, 'dashboard/pages/_form_generic.html', {
        'form': form,
        'page_title': f'{_("تعديل دار عرض")}: {media.title_ar}',
        'back_url': _smart_back_url(request, reverse('dashboard_app:media-screenings', args=[pk])),
    })


@login_required(login_url='dashboard_app:login')
def media_screening_delete(request, pk, screening_pk):
    screening = get_object_or_404(CinemaScreening, pk=screening_pk, media_id=pk)
    if request.method == 'POST':
        screening.delete()
    return redirect('dashboard_app:media-screenings', pk=pk)


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
            'title': _('مواقع الحجز'),
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
        'image_url': concert.display_poster_url or None,
        'stats': _event_counts_for(concert),
        'extra_actions': [
            {'label': _('روابط المنصات'), 'url': reverse('dashboard_app:entity-links', args=['concert', pk])},
        ],
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
# Advertisements
# ---------------------------------------------------------------------------

@login_required(login_url='dashboard_app:login')
def ads_list(request):
    queryset = Advertisement.objects.select_related('content_type').all()
    q = request.GET.get('q')
    if q:
        queryset = queryset.filter(title__icontains=q)
    ads = _paginate(request, queryset)
    for ad in ads:
        counts = _event_counts_for(ad)
        ad.views_count = counts[AnalyticsEvent.EventType.VIEW]
        ad.clicks_count = counts[AnalyticsEvent.EventType.EXTERNAL_CLICK]
    return render(request, 'dashboard/pages/ads/all.html', {
        'ads': ads,
        'querystring': _querystring(request),
    })


@login_required(login_url='dashboard_app:login')
def ad_create(request):
    return _save_form(
        request, AdvertisementForm, None, _('إضافة إعلان'), reverse('dashboard_app:ads'),
        'dashboard_app:ads',
    )


@login_required(login_url='dashboard_app:login')
def ad_edit(request, pk):
    ad = get_object_or_404(Advertisement, pk=pk)
    return _save_form(
        request, AdvertisementForm, ad, f'{_("تعديل إعلان")}: {ad.title}', reverse('dashboard_app:ads'),
        'dashboard_app:ads',
    )


@login_required(login_url='dashboard_app:login')
def ad_view(request, pk):
    ad = get_object_or_404(Advertisement, pk=pk)

    if ad.show_on_all_pages:
        placement_display = _('كل صفحات الموقع')
    else:
        labels = dict(Advertisement.Placement.choices)
        placement_display = '، '.join(str(labels.get(p, p)) for p in (ad.placements or [])) or '-'

    if ad.content_object is not None:
        linked_display = f'{ad.content_object} ({ad.content_type.model})'
    elif ad.external_url:
        linked_display = ad.external_url
    else:
        linked_display = _('غير مرتبط')

    fields = [
        (_('اسم الإعلان'), ad.title),
        (_('مفعّل'), _('نعم') if ad.is_active else _('لا')),
        (_('مرتبط بـ'), linked_display),
        (_('يظهر في'), placement_display),
    ]

    return render(request, 'dashboard/pages/_detail_generic.html', {
        'page_title': ad.title,
        'subtitle': _('نشط') if ad.is_active else _('متوقف'),
        'fields': fields,
        'image_url': ad.image.url if ad.image else None,
        'stats': _event_counts_for(ad),
        'edit_url': reverse('dashboard_app:ad-edit', args=[pk]),
        'back_url': _smart_back_url(request, reverse('dashboard_app:ads')),
    })


@login_required(login_url='dashboard_app:login')
def ad_delete(request, pk):
    ad = get_object_or_404(Advertisement, pk=pk)
    if request.method == 'POST':
        ad.delete()
    return redirect('dashboard_app:ads')


@login_required(login_url='dashboard_app:login')
def ad_toggle_active(request, pk):
    ad = get_object_or_404(Advertisement, pk=pk)
    if request.method == 'POST':
        ad.is_active = not ad.is_active
        ad.save(update_fields=['is_active'])
    return redirect('dashboard_app:ads')


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
        'image_url': platform.logo_icon_url or None,
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
# Cinema venues — a shared master list (like Platforms), managed once and
# picked per movie via "دور العرض" instead of retyping name/city each time.
# ---------------------------------------------------------------------------

@login_required(login_url='dashboard_app:login')
def cinema_venues_list(request):
    queryset = CinemaVenue.objects.all()
    q = request.GET.get('q')
    if q:
        queryset = queryset.filter(Q(name__icontains=q) | Q(city__icontains=q))
    venues = _paginate(request, queryset)
    return render(request, 'dashboard/pages/cinema_venues/all.html', {
        'venues': venues,
        'querystring': _querystring(request),
    })


@login_required(login_url='dashboard_app:login')
def cinema_venue_create(request):
    return _save_form(
        request, CinemaVenueForm, None, _('إضافة دار عرض'), reverse('dashboard_app:cinema-venues'),
        'dashboard_app:cinema-venues',
    )


@login_required(login_url='dashboard_app:login')
def cinema_venue_edit(request, pk):
    venue = get_object_or_404(CinemaVenue, pk=pk)
    return _save_form(
        request, CinemaVenueForm, venue, f'{_("تعديل")}: {venue.name}', reverse('dashboard_app:cinema-venues'),
        'dashboard_app:cinema-venues',
    )


@login_required(login_url='dashboard_app:login')
def cinema_venue_delete(request, pk):
    venue = get_object_or_404(CinemaVenue, pk=pk)
    if request.method == 'POST':
        venue.delete()
    return redirect('dashboard_app:cinema-venues')


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
