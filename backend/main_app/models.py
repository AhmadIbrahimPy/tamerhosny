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


class SongSimilarity(models.Model):
    """Precomputed "songs similar to this one" (see
    `backend.main_app.shared_utils.song_recommendations`) - collaborative
    where enough listening data exists (songs played by the same people,
    weighted the same way as the leaderboard's engagement score), falling
    back to content overlap (genre/mood/album/singers) for a song too new
    or too rarely played to have that data yet. Recomputed periodically,
    not on every play - a nightly batch job, not a live signal.
    """

    class Method(models.TextChoices):
        COLLABORATIVE = 'COLLABORATIVE', _('تعاوني (حسب المستمعين)')
        CONTENT = 'CONTENT', _('حسب المحتوى')

    song = models.ForeignKey(
        'music_app.Song', on_delete=models.CASCADE, related_name='similar_to',
    )
    similar_song = models.ForeignKey(
        'music_app.Song', on_delete=models.CASCADE, related_name='similar_from',
    )
    score = models.FloatField(default=0.0)
    method = models.CharField(max_length=15, choices=Method.choices)
    rank = models.PositiveSmallIntegerField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['song', 'similar_song']
        ordering = ['rank']
        indexes = [
            models.Index(fields=['song', 'rank']),
        ]

    def __str__(self):
        return f'{self.song} ~ {self.similar_song} (#{self.rank})'


class UserSongRecommendation(models.Model):
    """Precomputed "recommended for you" - a user's own SongSimilarity
    neighbors across everything they've listened to, weighted by how much
    they engaged with each source song (same decayed score as the
    leaderboard), excluding songs they've already played heavily. See
    `backend.main_app.shared_utils.song_recommendations`. Recomputed
    periodically alongside SongSimilarity, not live.
    """

    user = models.ForeignKey(
        UserAccount, on_delete=models.CASCADE, related_name='song_recommendations',
    )
    song = models.ForeignKey(
        'music_app.Song', on_delete=models.CASCADE, related_name='recommended_to',
    )
    score = models.FloatField(default=0.0)
    rank = models.PositiveSmallIntegerField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'song']
        ordering = ['rank']
        indexes = [
            models.Index(fields=['user', 'rank']),
        ]

    def __str__(self):
        return f'{self.user.username} - {self.song} (#{self.rank})'


class UserMoodScore(models.Model):
    """How much a user has been leaning into each Song.Mood recently, so
    "recommended for you" can lean the same way (see
    `backend.main_app.shared_utils.user_mood`) - someone on a two-day sad
    streak keeps getting sad-leaning suggestions, but if that fades and
    they're back to upbeat songs, so does this.

    One row per (user, mood) they've ever full-listened to something in.
    `decayed_score` is a snapshot as of `score_updated_at`, same
    exponential-decay approach as UserSongPlay/the leaderboard - a
    shorter half-life than that (a few days, not a week) since a mood is
    meant to read as "right now", not "this user's whole history".
    """

    # Mirrors music_app.models.Song.Mood (minus UNSPECIFIED) - duplicated
    # rather than imported to avoid a main_app -> music_app import at
    # module load time (Song itself only ever references main_app via
    # the 'main_app.Like' GenericRelation string, for the same reason).
    class Mood(models.TextChoices):
        ROMANTIC = 'ROMANTIC', _('Romantic / رومانسي')
        SAD_HEARTBREAK = 'SAD_HEARTBREAK', _('Sad & Heartbreak / حزين / دراما / جرح')
        ENERGETIC_UPBEAT = 'ENERGETIC_UPBEAT', _('Energetic & Upbeat / حماسي / طاقة عالية / أفراح')
        MOTIVATIONAL_HOPEFUL = 'MOTIVATIONAL_HOPEFUL', _('Motivational & Hopeful / تحفيزي / أمل وتفاؤل')
        CHILL_RELAXING = 'CHILL_RELAXING', _('Chill & Relaxing / رايق / هادئ للاسترخاء')
        NOSTALGIC = 'NOSTALGIC', _('Nostalgic / ذكريات وحنين')
        CONFIDENT_PLAYFUL = 'CONFIDENT_PLAYFUL', _('Confident & Playful / واثق / فريش')

    user = models.ForeignKey(
        UserAccount, on_delete=models.CASCADE, related_name='mood_scores',
    )
    mood = models.CharField(max_length=25, choices=Mood.choices)
    decayed_score = models.FloatField(default=0.0)
    score_updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['user', 'mood']
        indexes = [
            models.Index(fields=['user', 'mood']),
        ]

    def __str__(self):
        return f'{self.user.username} - {self.mood} ({self.decayed_score:.2f})'


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


class UserGameProfile(models.Model):
    """Site-wide gamification state for one user - points earned from
    activities across the whole site (not just one feature), plus a
    daily login-streak so coming back regularly is its own reward.
    Created lazily the first time a user does anything point-worthy.
    """

    user = models.OneToOneField(UserAccount, on_delete=models.CASCADE, related_name='game_profile')
    points = models.PositiveIntegerField(default=0)
    current_streak = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    last_active_date = models.DateField(null=True, blank=True)
    # A once-a-day snapshot of the leaderboard rank, purely so a
    # profile can show "your rank went up/down" - comparing against
    # points directly wouldn't work since points only ever go up, so a
    # rank comparison (against everyone else) is what can actually move
    # in either direction.
    previous_rank = models.PositiveIntegerField(null=True, blank=True)
    rank_snapshot_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ('-points',)

    def __str__(self):
        return f'{self.user} - {self.points} pts'


class PushSubscription(models.Model):
    """One browser's Web Push registration (from PushManager.subscribe())
    - the endpoint URL plus the two keys needed to encrypt a payload for
    it. `user` is nullable because permission can be granted, and a
    subscription created, before someone ever logs in; a later login on
    the same browser attaches it (see website_app views) so per-user
    sends (like the daily guess reminder) can reach it too. `endpoint` is
    unique because the browser can call subscribe() again for a device
    that's already registered (e.g. after a service worker update) and
    that must update the existing row, not create a duplicate.
    """

    endpoint = models.URLField(max_length=500, unique=True)
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
    user = models.ForeignKey(
        UserAccount, on_delete=models.CASCADE, related_name='push_subscriptions', null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user or "anonymous"} - {self.endpoint[:40]}...'


class VoiceAssistantLog(models.Model):
    """Diagnostic trail for the site-wide voice assistant (the "TH" wake
    word - see frontend/website/base.html), written by the browser
    itself at each lifecycle event as it happens. Mobile browsers barely
    honor SpeechRecognition's continuous:true - Android/iOS Chrome and
    Safari tear the whole recognition session down after nearly every
    utterance and restart it - which is invisible from the server side
    otherwise; this exists purely to see that restart/error pattern
    (and what got transcribed around it) after the fact, since it can't
    be reproduced on demand without the exact device/browser it happened
    on. Not meant to be permanent telemetry - safe to stop writing to
    or drop once the mobile behaviour it's tracking is understood.
    """

    class EventType(models.TextChoices):
        RECOGNITION_START = 'RECOGNITION_START', 'Recognition session started'
        RECOGNITION_END = 'RECOGNITION_END', 'Recognition session ended'
        RECOGNITION_ERROR = 'RECOGNITION_ERROR', 'Recognition error event'
        START_EXCEPTION = 'START_EXCEPTION', 'recognition.start() threw synchronously'
        WATCHDOG_RESTART = 'WATCHDOG_RESTART', 'Watchdog forced a restart'
        WAKE_DETECTED = 'WAKE_DETECTED', 'Wake word detected'
        COMMAND_MATCHED = 'COMMAND_MATCHED', 'Command matched locally and found something to play'
        COMMAND_NO_RESULT = 'COMMAND_NO_RESULT', 'Command matched locally but the search came up empty'
        COMMAND_IGNORED_GRACE = 'COMMAND_IGNORED_GRACE', 'Ignored as post-arm restart noise'
        COMMAND_AI_FALLBACK = 'COMMAND_AI_FALLBACK', 'Sent to the AI intent fallback'
        COMMAND_FAILED = 'COMMAND_FAILED', 'No match found anywhere'
        NETWORK_TOO_WEAK = 'NETWORK_TOO_WEAK', 'Skipped engaging the mic - network too weak'
        COMMAND_TENTATIVE_RESUME = 'COMMAND_TENTATIVE_RESUME', 'Bare "شغل"/"play" - waiting for a possible continuation'

    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        UserAccount, on_delete=models.SET_NULL, null=True, blank=True, related_name='voice_assistant_logs',
    )
    # One random id generated per page load (frontend) - not a login
    # session - so every event from the same visit/attempt can be
    # grouped together regardless of whether the visitor is logged in.
    client_session_id = models.CharField(max_length=32, blank=True)
    event_type = models.CharField(max_length=32, choices=EventType.choices)
    detail = models.CharField(max_length=255, blank=True)
    transcript = models.CharField(max_length=300, blank=True)
    # Generic numeric field, meaning depends on event_type: session
    # duration for RECOGNITION_END, time since the wake word armed for
    # WAKE_DETECTED/COMMAND_* events, etc. - see where each is written
    # from in base.html for the exact meaning.
    ms_value = models.IntegerField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ('-created_at',)
        indexes = [models.Index(fields=['client_session_id', 'created_at'])]

    def __str__(self):
        return f'{self.get_event_type_display()} - {self.created_at:%Y-%m-%d %H:%M:%S}'


class VoiceKnownPhrase(models.Model):
    """A voice command the fixed regex patterns in base.html couldn't
    match, classified once in the background by the same LLM chain
    voice_intent() already uses live (see
    backend.main_app.tasks.analyze_failed_voice_command, triggered from
    website_app.views.voice_log on a COMMAND_FAILED event) - along with
    a handful of AI-generated paraphrases of the same request in
    different wording.

    voice_intent() checks this table (fuzzy match against
    original_transcript and every paraphrase) before ever calling the
    LLM fresh - a request phrased similarly to one seen and classified
    before then resolves from this local table instantly, without a
    new API round-trip. Every field here is re-validated against the
    exact same fixed choices voice_intent() itself enforces before
    being trusted, regardless of what got stored - this table only
    ever short-circuits a lookup that would otherwise happen live, it
    never gets to introduce a new kind of action.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    original_transcript = models.CharField(max_length=300)
    intent = models.CharField(max_length=32)
    song_query = models.CharField(max_length=200, blank=True)
    mood = models.CharField(max_length=32, blank=True)
    lyrics_query = models.CharField(max_length=200, blank=True)
    page = models.CharField(max_length=64, blank=True)
    # AI-generated alternative phrasings of original_transcript with the
    # same meaning - checked alongside it on every future lookup.
    paraphrases = models.JSONField(default=list, blank=True)
    # How many times a later lookup actually matched this row - purely
    # to see which learned phrases are pulling their weight.
    hit_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f'{self.intent}: {self.original_transcript[:50]}'
