import random
from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserAccount(AbstractUser):
    class Role(models.IntegerChoices):
        ADMIN = 1, _('Admin')
        EDITOR = 2, _('Editor')
        VIEWER = 3, _('Viewer')

    role = models.PositiveSmallIntegerField(choices=Role.choices, default=Role.EDITOR)
    profile_image = models.ImageField(upload_to='users/profile_images/', blank=True, null=True, verbose_name=_('صورة الملف الشخصي'))

    # Roles allowed to log into the internal dashboard.
    DASHBOARD_ROLES = (Role.ADMIN, Role.EDITOR)

    def __str__(self):
        return self.username


class Like(models.Model):
    """نموذج للإعجاب - يسمح للمستخدمين بإضافة الأغاني والأفلام والحفلات إلى الإعجاب"""

    user = models.ForeignKey(
        UserAccount,
        on_delete=models.CASCADE,
        related_name='likes',
        verbose_name=_('المستخدم')
    )
    
    # Generic foreign key to support different content types
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to={
            'model__in': ['song', 'media', 'concert']
        },
        verbose_name=_('نوع المحتوى')
    )
    object_id = models.PositiveIntegerField(verbose_name=_('معرف المحتوى'))
    content_object = GenericForeignKey('content_type', 'object_id')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('تاريخ الإضافة'))

    class Meta:
        verbose_name = _('إعجاب')
        verbose_name_plural = _('الإعجاب')
        unique_together = ['user', 'content_type', 'object_id']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'content_type', 'object_id']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f'{self.user.username} - {self.content_object}'


class UserSongPlay(models.Model):
    """نموذج لتتبع تشغيل كل مستخدم لكل أغنية"""

    user = models.ForeignKey(
        UserAccount,
        on_delete=models.CASCADE,
        related_name='song_plays',
        verbose_name=_('المستخدم')
    )
    
    song = models.ForeignKey(
        'music_app.Song',
        on_delete=models.CASCADE,
        related_name='user_plays',
        verbose_name=_('الأغنية')
    )
    
    last_played_at = models.DateTimeField(auto_now=True, verbose_name=_('آخر تشغيل'))
    play_count = models.PositiveIntegerField(default=0, verbose_name=_('عدد مرات التشغيل للمستخدم'))

    # Engagement score for the "top listeners" leaderboard - only a full,
    # natural listen (reached the end, not skipped/paused early) adds to
    # it, and it decays over time so someone who binged this song months
    # ago doesn't keep outranking someone listening to it heavily today.
    # See backend.main_app.shared_utils.song_leaderboard for the decay
    # math; this column stores the score as of `score_updated_at`, not
    # a continuously-updated value.
    full_listen_count = models.PositiveIntegerField(default=0, verbose_name=_('عدد مرات الاستماع الكامل'))
    decayed_score = models.FloatField(default=0.0, verbose_name=_('نقاط التفاعل (متناقصة زمنياً)'))
    score_updated_at = models.DateTimeField(null=True, blank=True, verbose_name=_('آخر تحديث للنقاط'))

    class Meta:
        verbose_name = _('تشغيل مستخدم')
        verbose_name_plural = _('تشغيلات المستخدمين')
        unique_together = ['user', 'song']
        ordering = ['-last_played_at']
        indexes = [
            models.Index(fields=['user', 'song']),
            models.Index(fields=['last_played_at']),
        ]

    def __str__(self):
        return f'{self.user.username} - {self.song}'


class CurrentSongListener(models.Model):
    """نموذج لتتبع المستخدمين الذين يستمعون حالياً لأغنية معينة"""

    user = models.ForeignKey(
        UserAccount,
        on_delete=models.CASCADE,
        related_name='current_listening',
        verbose_name=_('المستخدم'),
        null=True,
        blank=True
    )
    
    session_key = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('مفتاح الجلسة')
    )
    
    song = models.ForeignKey(
        'music_app.Song',
        on_delete=models.CASCADE,
        related_name='current_listeners',
        verbose_name=_('الأغنية')
    )
    
    started_at = models.DateTimeField(auto_now_add=True, verbose_name=_('وقت البدء'))
    last_heartbeat = models.DateTimeField(auto_now=True, verbose_name=_('آخر نبض'))

    class Meta:
        verbose_name = _('مستخدم حالي')
        verbose_name_plural = _('المستخدمون الحاليون')
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'song'],
                condition=models.Q(user__isnull=False),
                name='unique_user_song'
            ),
            models.UniqueConstraint(
                fields=['session_key', 'song'],
                condition=models.Q(user__isnull=True),
                name='unique_session_song'
            )
        ]
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['user', 'song']),
            models.Index(fields=['song']),
            models.Index(fields=['last_heartbeat']),
        ]

    def __str__(self):
        if self.user:
            return f'{self.user.username} - {self.song}'
        return f'Session {self.session_key[:8]} - {self.song}'


class Playlist(models.Model):
    """نموذج للبلاي لست - قوائم تشغيل مخصصة للمستخدمين"""

    user = models.ForeignKey(
        UserAccount,
        on_delete=models.CASCADE,
        related_name='playlists',
        verbose_name=_('المستخدم')
    )
    name = models.CharField(max_length=200, verbose_name=_('اسم القائمة'))
    description = models.TextField(blank=True, verbose_name=_('الوصف'))
    is_public = models.BooleanField(default=False, verbose_name=_('عامة'))
    cover_image = models.ImageField(
        upload_to='playlists/covers/',
        blank=True,
        null=True,
        verbose_name=_('صورة الغلاف')
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('تاريخ الإنشاء'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('تاريخ التحديث'))

    class Meta:
        verbose_name = _('قائمة تشغيل')
        verbose_name_plural = _('قوائم التشغيل')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} - {self.name}'


class PlaylistItem(models.Model):
    """عناصر قائمة التشغيل - ربط الأغاني بقوائم التشغيل"""

    playlist = models.ForeignKey(
        Playlist,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('قائمة التشغيل')
    )
    song = models.ForeignKey(
        'music_app.Song',
        on_delete=models.CASCADE,
        related_name='playlist_items',
        verbose_name=_('الأغنية')
    )
    order = models.PositiveIntegerField(default=0, verbose_name=_('الترتيب'))
    added_at = models.DateTimeField(auto_now_add=True, verbose_name=_('تاريخ الإضافة'))

    class Meta:
        verbose_name = _('عنصر قائمة التشغيل')
        verbose_name_plural = _('عناصر قوائم التشغيل')
        ordering = ['order', 'added_at']
        unique_together = ['playlist', 'song']

    def __str__(self):
        return f'{self.playlist.name} - {self.song.title_ar}'


class PasswordResetCode(models.Model):
    """A short-lived 6-digit code emailed for the public site's
    forgot-password flow (separate from the internal dashboard login).
    """

    EXPIRY = timedelta(minutes=15)

    user = models.ForeignKey(
        UserAccount,
        on_delete=models.CASCADE,
        related_name='password_reset_codes',
        verbose_name=_('المستخدم'),
    )
    code = models.CharField(max_length=6, verbose_name=_('الكود'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('تاريخ الإنشاء'))
    used_at = models.DateTimeField(null=True, blank=True, verbose_name=_('تاريخ الاستخدام'))

    class Meta:
        verbose_name = _('كود استعادة كلمة السر')
        verbose_name_plural = _('أكواد استعادة كلمة السر')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'code']),
        ]

    @classmethod
    def generate(cls, user):
        cls.objects.filter(user=user, used_at__isnull=True).delete()
        return cls.objects.create(user=user, code=f'{random.randint(0, 999999):06d}')

    @property
    def is_valid(self):
        return self.used_at is None and timezone.now() - self.created_at <= self.EXPIRY

    def __str__(self):
        return f'{self.user.username} - {self.code}'


class SongLeaderboardRank(models.Model):
    """The last-computed "top engaged listeners" ranking for a song (see
    `backend.main_app.shared_utils.song_leaderboard`) - who has listened
    to it the most, weighted toward recent full listens, with a bonus
    for having liked it. Persisted so a newly-connecting viewer sees the
    board immediately, and so the next recompute has a baseline to diff
    against for the up/down/same/new trend arrows.
    """

    class Trend(models.TextChoices):
        UP = 'UP', _('صاعد')
        DOWN = 'DOWN', _('هابط')
        SAME = 'SAME', _('ثابت')
        NEW = 'NEW', _('جديد')

    song = models.ForeignKey(
        'music_app.Song', on_delete=models.CASCADE, related_name='leaderboard_ranks',
    )
    user = models.ForeignKey(
        UserAccount, on_delete=models.CASCADE, related_name='song_leaderboard_ranks',
    )
    rank = models.PositiveSmallIntegerField()
    score = models.FloatField(default=0.0)
    full_listen_count = models.PositiveIntegerField(default=0)
    is_liked = models.BooleanField(default=False)
    trend = models.CharField(max_length=4, choices=Trend.choices, default=Trend.NEW)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['song', 'user']
        ordering = ['rank']
        indexes = [
            models.Index(fields=['song', 'rank']),
        ]

    def __str__(self):
        return f'{self.song} - #{self.rank} {self.user.username}'


class LoginSession(models.Model):
    """A record of one successful login, captured for security auditing:
    when it happened, from what device/IP, and whether it was a dashboard
    (admin/editor) login or a regular app/site login.
    """

    class Source(models.TextChoices):
        DASHBOARD = 'DASHBOARD', _('لوحة التحكم')
        APP = 'APP', _('التطبيق / الموقع')

    user = models.ForeignKey(
        UserAccount, on_delete=models.CASCADE, related_name='login_sessions',
    )
    source = models.CharField(max_length=10, choices=Source.choices)
    is_admin = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    device = models.CharField(max_length=150, blank=True)
    country_code = models.CharField(max_length=2, blank=True)
    country_name = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f'{self.user} - {self.created_at:%Y-%m-%d %H:%M}'
