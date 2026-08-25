from django import forms
from django.utils.translation import gettext_lazy as _

from backend.concerts_app.models import Concert
from backend.dashboard_app.widgets import CircularAvatarWidget, SquareCoverWidget
from backend.links_app.models import Platform
from backend.main_app.models import UserAccount
from backend.media_app.models import Media
from backend.music_app.models import Album, Song, SongLyricSegment
from backend.people_app.models import Person
from backend.studios_app.models import Studio

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
            'title_ar', 'title_en', 'release_date', 'cover_art_url', 'record_label',
            'visibility', 'publish_at',
        ]
        labels = {
            'title_ar': _('العنوان بالعربية'),
            'title_en': _('العنوان بالإنجليزية'),
            'release_date': _('تاريخ الإصدار'),
            'cover_art_url': _('رابط صورة الغلاف'),
            'record_label': _('شركة الإنتاج'),
            'visibility': _('حالة الظهور'),
            'publish_at': _('موعد النشر'),
        }
        widgets = {
            'title_ar': forms.TextInput(attrs=WIDGET_ATTRS),
            'title_en': forms.TextInput(attrs=WIDGET_ATTRS),
            'release_date': forms.DateInput(attrs={**WIDGET_ATTRS, 'type': 'date'}),
            'cover_art_url': forms.URLInput(attrs=WIDGET_ATTRS),
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
            'title_ar', 'title_en', 'cover_image', 'song_type', 'duration_seconds', 'lyrics', 'release_year',
            'is_duet', 'recording_studio', 'album', 'related_media', 'visibility', 'publish_at',
        ]
        labels = {
            'title_ar': _('العنوان بالعربية'),
            'title_en': _('العنوان بالإنجليزية'),
            'cover_image': _('صورة الأغنية'),
            'song_type': _('النوع'),
            'duration_seconds': _('المدة (بالثواني)'),
            'lyrics': _('الكلمات'),
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
            'song_type': forms.Select(attrs=SELECT_ATTRS),
            'duration_seconds': forms.NumberInput(attrs=WIDGET_ATTRS),
            'lyrics': forms.Textarea(attrs={**WIDGET_ATTRS, 'rows': 5}),
            'release_year': forms.NumberInput(attrs=WIDGET_ATTRS),
            'is_duet': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'recording_studio': forms.Select(attrs=SELECT_ATTRS),
            'album': forms.Select(attrs=SELECT_ATTRS),
            'related_media': forms.Select(attrs=SELECT_ATTRS),
            'visibility': forms.Select(attrs=SELECT_ATTRS),
            'publish_at': forms.DateTimeInput(attrs={**WIDGET_ATTRS, 'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ('recording_studio', 'album', 'related_media'):
            self.fields[field_name].empty_label = NONE_CHOICE


class MediaForm(forms.ModelForm):
    class Meta:
        model = Media
        fields = [
            'title_ar', 'title_en', 'media_type', 'release_date', 'poster_url', 'synopsis', 'rating',
            'advertiser_company', 'brand_name', 'campaign_concept', 'visibility', 'publish_at',
        ]
        labels = {
            'title_ar': _('العنوان بالعربية'),
            'title_en': _('العنوان بالإنجليزية'),
            'media_type': _('النوع'),
            'release_date': _('تاريخ الإصدار'),
            'poster_url': _('رابط البوستر'),
            'synopsis': _('القصة'),
            'rating': _('التقييم'),
            'advertiser_company': _('جهة الإعلان'),
            'brand_name': _('اسم العلامة التجارية'),
            'campaign_concept': _('فكرة الحملة'),
            'visibility': _('حالة الظهور'),
            'publish_at': _('موعد النشر'),
        }
        widgets = {
            'title_ar': forms.TextInput(attrs=WIDGET_ATTRS),
            'title_en': forms.TextInput(attrs=WIDGET_ATTRS),
            'media_type': forms.Select(attrs=SELECT_ATTRS),
            'release_date': forms.DateInput(attrs={**WIDGET_ATTRS, 'type': 'date'}),
            'poster_url': forms.URLInput(attrs=WIDGET_ATTRS),
            'synopsis': forms.Textarea(attrs={**WIDGET_ATTRS, 'rows': 4}),
            'rating': forms.NumberInput(attrs={**WIDGET_ATTRS, 'step': '0.1', 'min': 0, 'max': 10}),
            'advertiser_company': forms.TextInput(attrs=WIDGET_ATTRS),
            'brand_name': forms.TextInput(attrs=WIDGET_ATTRS),
            'campaign_concept': forms.Textarea(attrs={**WIDGET_ATTRS, 'rows': 3}),
            'visibility': forms.Select(attrs=SELECT_ATTRS),
            'publish_at': forms.DateTimeInput(attrs={**WIDGET_ATTRS, 'type': 'datetime-local'}),
        }


class ConcertForm(forms.ModelForm):
    class Meta:
        model = Concert
        fields = [
            'title_ar', 'title_en', 'status', 'date', 'venue_name', 'city', 'country',
            'description', 'poster_url', 'organizer', 'visibility', 'publish_at',
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
            'poster_url': _('رابط البوستر'),
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
            'poster_url': forms.URLInput(attrs=WIDGET_ATTRS),
            'organizer': forms.Select(attrs=SELECT_ATTRS),
            'visibility': forms.Select(attrs=SELECT_ATTRS),
            'publish_at': forms.DateTimeInput(attrs={**WIDGET_ATTRS, 'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['organizer'].empty_label = NONE_CHOICE


class SongLyricSegmentForm(forms.ModelForm):
    class Meta:
        model = SongLyricSegment
        fields = ['start_seconds', 'end_seconds', 'segment_type', 'text']
        labels = {
            'start_seconds': _('من (ثانية)'),
            'end_seconds': _('إلى (ثانية)'),
            'segment_type': _('نوع المقطع'),
            'text': _('النص'),
        }
        widgets = {
            'start_seconds': forms.NumberInput(attrs={**WIDGET_ATTRS, 'step': '0.01', 'min': 0}),
            'end_seconds': forms.NumberInput(attrs={**WIDGET_ATTRS, 'step': '0.01', 'min': 0}),
            'segment_type': forms.Select(attrs=SELECT_ATTRS),
            'text': forms.Textarea(attrs={**WIDGET_ATTRS, 'rows': 2}),
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


class PlatformForm(forms.ModelForm):
    class Meta:
        model = Platform
        fields = ['platform_name', 'logo_icon_url']
        labels = {
            'platform_name': _('المنصة'),
            'logo_icon_url': _('رابط الأيقونة'),
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
