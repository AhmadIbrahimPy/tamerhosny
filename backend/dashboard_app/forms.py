from django import forms
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

from backend.ads_app.models import Advertisement
from backend.concerts_app.models import Concert
from backend.dashboard_app.widgets import CircularAvatarWidget, SquareCoverWidget
from backend.links_app.models import ExternalLink, Platform
from backend.main_app.models import UserAccount
from backend.media_app.models import CinemaScreening, CinemaVenue, Media, MediaCredit
from backend.music_app.models import Album, Song, SongCredit, SongLyricSegment
from backend.people_app.models import Person
from backend.studios_app.models import Studio

# kind -> (Model, display-name field) for the ad's optional internal link.
AD_LINK_KINDS = {
    'person': (Person, 'full_name_ar'),
    'album': (Album, 'title_ar'),
    'song': (Song, 'title_ar'),
    'media': (Media, 'title_ar'),
    'concert': (Concert, 'title_ar'),
}

WIDGET_ATTRS = {'class': 'form-control'}
SELECT_ATTRS = {'class': 'form-select'}
NONE_CHOICE = _('-- بدون --')


class PersonForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = ['full_name_ar', 'full_name_en', 'primary_role', 'bio', 'profile_image']
        labels = {
            'full_name_ar': _('الاسم بالعربية'),
            'full_name_en': _('الاسم بالإنجليزية'),
            'primary_role': _('الدور الأساسي'),
            'bio': _('نبذة'),
            'profile_image': _('الصورة'),
        }
        widgets = {
            'full_name_ar': forms.TextInput(attrs=WIDGET_ATTRS),
            'full_name_en': forms.TextInput(attrs=WIDGET_ATTRS),
            'primary_role': forms.Select(attrs=SELECT_ATTRS),
            'bio': forms.Textarea(attrs={**WIDGET_ATTRS, 'rows': 4}),
            'profile_image': CircularAvatarWidget(),
        }


class StudioForm(forms.ModelForm):
    class Meta:
        model = Studio
        fields = ['name', 'entity_type', 'logo']
        labels = {
            'name': _('الاسم'),
            'entity_type': _('النوع'),
            'logo': _('الشعار'),
        }
        widgets = {
            'name': forms.TextInput(attrs=WIDGET_ATTRS),
            'entity_type': forms.Select(attrs=SELECT_ATTRS),
            'logo': CircularAvatarWidget(),
        }


class AlbumForm(forms.ModelForm):
    class Meta:
        model = Album
        fields = [
            'title_ar', 'title_en', 'release_date', 'cover_image', 'cover_art_url', 'cover_video',
            'record_label', 'visibility', 'publish_at',
        ]
        labels = {
            'title_ar': _('العنوان بالعربية'),
            'title_en': _('العنوان بالإنجليزية'),
            'release_date': _('تاريخ الإصدار'),
            'cover_image': _('صورة الغلاف'),
            'cover_art_url': _('رابط صورة الغلاف (اختياري)'),
            'cover_video': _('فيديو خلفية الصفحة (اختياري)'),
            'record_label': _('شركة الإنتاج'),
            'visibility': _('حالة الظهور'),
            'publish_at': _('موعد النشر'),
        }
        widgets = {
            'title_ar': forms.TextInput(attrs=WIDGET_ATTRS),
            'title_en': forms.TextInput(attrs=WIDGET_ATTRS),
            'release_date': forms.DateInput(attrs={**WIDGET_ATTRS, 'type': 'date'}),
            'cover_image': SquareCoverWidget(),
            'cover_art_url': forms.URLInput(attrs=WIDGET_ATTRS),
            'cover_video': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'video/*'}),
            'record_label': forms.Select(attrs=SELECT_ATTRS),
            'visibility': forms.Select(attrs=SELECT_ATTRS),
            'publish_at': forms.DateTimeInput(attrs={**WIDGET_ATTRS, 'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['record_label'].empty_label = NONE_CHOICE


class SongForm(forms.ModelForm):
    class Meta:
        model = Song
        fields = [
            'title_ar', 'title_en', 'cover_image', 'audio_file', 'cover_video', 'song_type',
            'genre', 'mood', 'duration_seconds', 'release_year', 'is_duet', 'recording_studio', 'album', 'related_media',
            'visibility', 'publish_at',
        ]
        labels = {
            'title_ar': _('العنوان بالعربية'),
            'title_en': _('العنوان بالإنجليزية'),
            'cover_image': _('صورة الأغنية'),
            'audio_file': _('ملف الصوت'),
            'cover_video': _('فيديو خلفية الصفحة (اختياري)'),
            'song_type': _('النوع'),
            'genre': _('النوع الموسيقي'),
            'mood': _('الحالة المزاجية'),
            'duration_seconds': _('المدة (بالثواني)'),
            'release_year': _('سنة الإصدار'),
            'is_duet': _('دويتو'),
            'recording_studio': _('استوديو التسجيل'),
            'album': _('الألبوم'),
            'related_media': _('العمل الفني المرتبط'),
            'visibility': _('حالة الظهور'),
            'publish_at': _('موعد النشر'),
        }
        widgets = {
            'title_ar': forms.TextInput(attrs=WIDGET_ATTRS),
            'title_en': forms.TextInput(attrs=WIDGET_ATTRS),
            'cover_image': SquareCoverWidget(),
            'audio_file': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'audio/*'}),
            'cover_video': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'video/*'}),
            'song_type': forms.Select(attrs=SELECT_ATTRS),
            'genre': forms.Select(attrs=SELECT_ATTRS),
            'mood': forms.Select(attrs=SELECT_ATTRS),
            'duration_seconds': forms.NumberInput(attrs=WIDGET_ATTRS),
            'release_year': forms.NumberInput(attrs={**WIDGET_ATTRS, 'id': 'id_release_year'}),
            'is_duet': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'recording_studio': forms.Select(attrs=SELECT_ATTRS),
            'album': forms.Select(attrs={**SELECT_ATTRS, 'id': 'id_album'}),
            'related_media': forms.Select(attrs=SELECT_ATTRS),
            'visibility': forms.Select(attrs=SELECT_ATTRS),
            'publish_at': forms.DateTimeInput(attrs={**WIDGET_ATTRS, 'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ('recording_studio', 'album', 'related_media'):
            self.fields[field_name].empty_label = NONE_CHOICE
        self.fields['release_year'].help_text = _(
            'بيتحدد تلقائيًا من سنة إصدار الألبوم لو اخترت ألبوم، وتقدر تعدّله يدويًا.'
        )
        self.fields['is_duet'].help_text = _(
            'بعد حفظ الأغنية، زوّد المشارك التاني من قسم "طقم العمل والمشاركين" في صفحة الأغنية.'
        )


class SongCreditForm(forms.ModelForm):
    class Meta:
        model = SongCredit
        fields = ['person', 'role']
        labels = {
            'person': _('الشخص'),
            'role': _('الدور'),
        }
        widgets = {
            'person': forms.Select(attrs=SELECT_ATTRS),
            'role': forms.Select(attrs=SELECT_ATTRS),
        }


class _BaseWorkForm(forms.ModelForm):
    """Shared editable fields for a movie/series/program entry (everything
    except the commercial-only attributes). Each subclass pins media_type
    so the three sections stay fully separate in the dashboard.
    """
    media_type = None

    class Meta:
        model = Media
        fields = [
            'title_ar', 'title_en', 'poster_image', 'poster_url', 'cover_video',
            'release_date', 'synopsis', 'rating', 'visibility', 'publish_at',
        ]
        labels = {
            'title_ar': _('العنوان بالعربية'),
            'title_en': _('العنوان بالإنجليزية'),
            'poster_image': _('صورة العمل'),
            'poster_url': _('رابط بوستر بديل (اختياري)'),
            'cover_video': _('فيديو خلفية الصفحة (اختياري)'),
            'release_date': _('تاريخ الإصدار'),
            'synopsis': _('القصة'),
            'rating': _('التقييم'),
            'visibility': _('حالة الظهور'),
            'publish_at': _('موعد النشر'),
        }
        widgets = {
            'title_ar': forms.TextInput(attrs=WIDGET_ATTRS),
            'title_en': forms.TextInput(attrs=WIDGET_ATTRS),
            'poster_image': SquareCoverWidget(),
            'poster_url': forms.URLInput(attrs=WIDGET_ATTRS),
            'cover_video': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'video/*'}),
            'release_date': forms.DateInput(attrs={**WIDGET_ATTRS, 'type': 'date'}),
            'synopsis': forms.Textarea(attrs={**WIDGET_ATTRS, 'rows': 4}),
            'rating': forms.NumberInput(attrs={**WIDGET_ATTRS, 'step': '0.1', 'min': 0, 'max': 10}),
            'visibility': forms.Select(attrs=SELECT_ATTRS),
            'publish_at': forms.DateTimeInput(attrs={**WIDGET_ATTRS, 'type': 'datetime-local'}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.media_type = self.media_type
        if commit:
            instance.save()
        return instance


class MovieForm(_BaseWorkForm):
    media_type = Media.MediaType.MOVIE


class SeriesForm(_BaseWorkForm):
    media_type = Media.MediaType.TV_SERIES


class ProgramForm(_BaseWorkForm):
    media_type = Media.MediaType.PROGRAM


class CommercialForm(forms.ModelForm):
    media_type = Media.MediaType.COMMERCIAL

    class Meta:
        model = Media
        fields = [
            'title_ar', 'title_en', 'poster_image', 'poster_url', 'cover_video',
            'release_date', 'advertiser_company', 'brand_name', 'campaign_concept', 'visibility', 'publish_at',
        ]
        labels = {
            'title_ar': _('العنوان بالعربية'),
            'title_en': _('العنوان بالإنجليزية'),
            'poster_image': _('صورة الإعلان'),
            'poster_url': _('رابط صورة بديل (اختياري)'),
            'cover_video': _('فيديو خلفية الصفحة (اختياري)'),
            'release_date': _('تاريخ الإصدار'),
            'advertiser_company': _('جهة الإعلان'),
            'brand_name': _('اسم العلامة التجارية'),
            'campaign_concept': _('فكرة الحملة'),
            'visibility': _('حالة الظهور'),
            'publish_at': _('موعد النشر'),
        }
        widgets = {
            'title_ar': forms.TextInput(attrs=WIDGET_ATTRS),
            'title_en': forms.TextInput(attrs=WIDGET_ATTRS),
            'poster_image': SquareCoverWidget(),
            'poster_url': forms.URLInput(attrs=WIDGET_ATTRS),
            'cover_video': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'video/*'}),
            'release_date': forms.DateInput(attrs={**WIDGET_ATTRS, 'type': 'date'}),
            'advertiser_company': forms.TextInput(attrs=WIDGET_ATTRS),
            'brand_name': forms.TextInput(attrs=WIDGET_ATTRS),
            'campaign_concept': forms.Textarea(attrs={**WIDGET_ATTRS, 'rows': 3}),
            'visibility': forms.Select(attrs=SELECT_ATTRS),
            'publish_at': forms.DateTimeInput(attrs={**WIDGET_ATTRS, 'type': 'datetime-local'}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.media_type = self.media_type
        if commit:
            instance.save()
        return instance


MEDIA_SECTION_FORMS = {
    'movies': MovieForm,
    'series': SeriesForm,
    'commercials': CommercialForm,
    'programs': ProgramForm,
}


class MediaCreditForm(forms.ModelForm):
    class Meta:
        model = MediaCredit
        fields = ['person', 'role', 'character_name']
        labels = {
            'person': _('الشخص'),
            'role': _('الدور'),
            'character_name': _('اسم الشخصية (للممثلين، اختياري)'),
        }
        widgets = {
            'person': forms.Select(attrs=SELECT_ATTRS),
            'role': forms.Select(attrs=SELECT_ATTRS),
            'character_name': forms.TextInput(attrs=WIDGET_ATTRS),
        }


class CinemaVenueForm(forms.ModelForm):
    class Meta:
        model = CinemaVenue
        fields = ['name', 'city']
        labels = {
            'name': _('اسم دار العرض'),
            'city': _('المدينة'),
        }
        widgets = {
            'name': forms.TextInput(attrs=WIDGET_ATTRS),
            'city': forms.TextInput(attrs=WIDGET_ATTRS),
        }


class ScreeningForm(forms.ModelForm):
    class Meta:
        model = CinemaScreening
        fields = ['venue', 'ticket_price', 'booking_url']
        labels = {
            'venue': _('دار العرض'),
            'ticket_price': _('سعر التذكرة'),
            'booking_url': _('رابط الحجز (اختياري)'),
        }
        widgets = {
            'venue': forms.Select(attrs=SELECT_ATTRS),
            'ticket_price': forms.NumberInput(attrs={**WIDGET_ATTRS, 'step': '0.01', 'min': 0}),
            'booking_url': forms.URLInput(attrs=WIDGET_ATTRS),
        }


class ConcertForm(forms.ModelForm):
    class Meta:
        model = Concert
        fields = [
            'title_ar', 'title_en', 'status', 'date', 'venue_name', 'city', 'country',
            'description', 'poster_image', 'poster_url', 'cover_video',
            'latitude', 'longitude', 'organizer', 'visibility', 'publish_at',
        ]
        labels = {
            'title_ar': _('العنوان بالعربية'),
            'title_en': _('العنوان بالإنجليزية'),
            'status': _('حالة الحفلة'),
            'date': _('التاريخ'),
            'venue_name': _('المكان'),
            'city': _('المدينة'),
            'country': _('الدولة'),
            'description': _('الوصف'),
            'poster_image': _('صورة الحفلة'),
            'poster_url': _('رابط بوستر بديل (اختياري)'),
            'cover_video': _('فيديو خلفية الصفحة (اختياري)'),
            'latitude': _('خط العرض'),
            'longitude': _('خط الطول'),
            'organizer': _('الجهة المنظمة'),
            'visibility': _('حالة الظهور'),
            'publish_at': _('موعد النشر'),
        }
        widgets = {
            'title_ar': forms.TextInput(attrs=WIDGET_ATTRS),
            'title_en': forms.TextInput(attrs=WIDGET_ATTRS),
            'status': forms.Select(attrs=SELECT_ATTRS),
            'date': forms.DateTimeInput(attrs={**WIDGET_ATTRS, 'type': 'datetime-local'}),
            'venue_name': forms.TextInput(attrs=WIDGET_ATTRS),
            'city': forms.TextInput(attrs=WIDGET_ATTRS),
            'country': forms.TextInput(attrs=WIDGET_ATTRS),
            'description': forms.Textarea(attrs={**WIDGET_ATTRS, 'rows': 4}),
            'poster_image': SquareCoverWidget(),
            'poster_url': forms.URLInput(attrs=WIDGET_ATTRS),
            'cover_video': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'video/*'}),
            'latitude': forms.HiddenInput(attrs={'id': 'id_latitude'}),
            'longitude': forms.HiddenInput(attrs={'id': 'id_longitude'}),
            'organizer': forms.Select(attrs=SELECT_ATTRS),
            'visibility': forms.Select(attrs=SELECT_ATTRS),
            'publish_at': forms.DateTimeInput(attrs={**WIDGET_ATTRS, 'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['organizer'].empty_label = NONE_CHOICE
        # Plain decimal notation always (never locale-formatted with a
        # comma decimal separator), since these feed a JS map picker.
        self.fields['latitude'].localize = False
        self.fields['longitude'].localize = False


class SongLyricSegmentForm(forms.ModelForm):
    class Meta:
        model = SongLyricSegment
        fields = ['start_seconds', 'end_seconds', 'segment_type', 'text', 'vocal_doubling', 'double_tracking']
        labels = {
            'start_seconds': _('من (ثانية)'),
            'end_seconds': _('إلى (ثانية)'),
            'segment_type': _('نوع المقطع'),
            'text': _('النص'),
            'vocal_doubling': _('تكرار الصوت'),
            'double_tracking': _('تتبع مزدوج'),
        }
        widgets = {
            'start_seconds': forms.NumberInput(attrs={**WIDGET_ATTRS, 'step': '0.01', 'min': 0}),
            'end_seconds': forms.NumberInput(attrs={**WIDGET_ATTRS, 'step': '0.01', 'min': 0}),
            'segment_type': forms.Select(attrs=SELECT_ATTRS),
            'text': forms.Textarea(attrs={**WIDGET_ATTRS, 'rows': 2}),
            'vocal_doubling': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'double_tracking': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('start_seconds')
        end = cleaned.get('end_seconds')
        if start is not None and end is not None and end <= start:
            raise forms.ValidationError(_('وقت النهاية لازم يكون بعد وقت البداية.'))
        if cleaned.get('segment_type') == SongLyricSegment.SegmentType.LYRICS and not cleaned.get('text', '').strip():
            self.add_error('text', _('لازم تكتب الكلمات لأن نوع المقطع "كلمات".'))
        return cleaned


class ExternalLinkForm(forms.ModelForm):
    class Meta:
        model = ExternalLink
        fields = ['platform', 'direct_url', 'access_type', 'embed_code']
        labels = {
            'platform': _('المنصة'),
            'direct_url': _('الرابط'),
            'access_type': _('نوع الوصول'),
            'embed_code': _('كود التضمين (اختياري)'),
        }
        widgets = {
            'platform': forms.Select(attrs=SELECT_ATTRS),
            'direct_url': forms.URLInput(attrs=WIDGET_ATTRS),
            'access_type': forms.Select(attrs=SELECT_ATTRS),
            'embed_code': forms.Textarea(attrs={**WIDGET_ATTRS, 'rows': 2}),
        }


class PlatformForm(forms.ModelForm):
    class Meta:
        model = Platform
        fields = ['platform_name', 'logo_icon_url']
        labels = {
            'platform_name': _('المنصة'),
            'logo_icon_url': _('رابط صورة الأيقونة'),
        }
        help_texts = {
            'logo_icon_url': _(
                'رابط مباشر لصورة الأيقونة (لازم ينتهي بامتداد صورة زي .png أو .jpg أو .svg)، '
                'مش رابط صفحة عادية زي رابط تطبيق أو موقع.'
            ),
        }
        widgets = {
            'platform_name': forms.Select(attrs=SELECT_ATTRS),
            'logo_icon_url': forms.URLInput(attrs=WIDGET_ATTRS),
        }


class UserAccountForm(forms.ModelForm):
    password = forms.CharField(
        label=_('كلمة المرور'),
        widget=forms.PasswordInput(attrs=WIDGET_ATTRS), required=False,
        help_text=_('اتركه فارغاً للإبقاء على كلمة المرور الحالية عند التعديل.'),
    )

    class Meta:
        model = UserAccount
        fields = ['username', 'email', 'role', 'is_active']
        labels = {
            'username': _('اسم المستخدم'),
            'email': _('البريد الإلكتروني'),
            'role': _('الدور'),
            'is_active': _('مفعّل'),
        }
        widgets = {
            'username': forms.TextInput(attrs=WIDGET_ATTRS),
            'email': forms.EmailInput(attrs=WIDGET_ATTRS),
            'role': forms.Select(attrs=SELECT_ATTRS),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        elif not user.pk:
            user.set_unusable_password()
        if commit:
            user.save()
        return user


class AdvertisementForm(forms.ModelForm):
    placements = forms.MultipleChoiceField(
        choices=Advertisement.Placement.choices, required=False,
        widget=forms.CheckboxSelectMultiple, label=_('الصفحات المحددة (لو مش هيظهر في كل الصفحات)'),
    )

    class Meta:
        model = Advertisement
        fields = ['title', 'image', 'is_active', 'external_url', 'show_on_all_pages']
        labels = {
            'title': _('اسم الإعلان (للإدارة فقط)'),
            'image': _('صورة الإعلان'),
            'is_active': _('مفعّل'),
            'external_url': _('رابط موقع خارجي (اختياري، لو مش مرتبط بعنصر داخلي)'),
            'show_on_all_pages': _('يظهر في كل صفحات الموقع'),
        }
        widgets = {
            'title': forms.TextInput(attrs=WIDGET_ATTRS),
            'image': SquareCoverWidget(),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'external_url': forms.URLInput(attrs=WIDGET_ATTRS),
            'show_on_all_pages': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance')
        linked_kind = instance.content_type.model if (instance and instance.content_type_id) else None
        for kind, (model, name_field) in AD_LINK_KINDS.items():
            field_name = f'link_{kind}'
            self.fields[field_name] = forms.ModelChoiceField(
                queryset=model.objects.all(), required=False, empty_label=NONE_CHOICE,
                label=_('مرتبط بـ') + f' {model._meta.verbose_name}',
                widget=forms.Select(attrs=SELECT_ATTRS),
            )
            if instance and linked_kind == kind:
                self.initial[field_name] = instance.object_id
        if instance and instance.pk:
            self.initial['placements'] = instance.placements or []

    def clean(self):
        cleaned = super().clean()
        chosen = [(kind, cleaned.get(f'link_{kind}')) for kind in AD_LINK_KINDS if cleaned.get(f'link_{kind}')]
        if len(chosen) > 1:
            raise forms.ValidationError(_('اختر عنصر واحد بس تربط بيه الإعلان.'))
        if chosen and cleaned.get('external_url'):
            raise forms.ValidationError(_('الإعلان يتربط إما بعنصر داخلي أو برابط خارجي، مش الاتنين.'))
        if not cleaned.get('show_on_all_pages') and not cleaned.get('placements'):
            self.add_error('placements', _('اختر صفحة واحدة على الأقل، أو فعّل "يظهر في كل الصفحات".'))
        self._resolved_link = chosen[0] if chosen else None
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self._resolved_link:
            _, obj = self._resolved_link
            instance.content_type = ContentType.objects.get_for_model(type(obj))
            instance.object_id = obj.pk
        else:
            instance.content_type = None
            instance.object_id = None
        instance.placements = self.cleaned_data.get('placements') or []
        if commit:
            instance.save()
        return instance
