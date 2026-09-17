"""Celery tasks: the "Sing With Tamer" duet mix, and the daily
"خمّن الأغنية" push-notification reminder (see config/celery.py's
beat_schedule for when the latter fires).

Vocal removal (AI) + audio mixing is slow enough that running it inside
the request/response cycle would block a whole Daphne process (see
config/settings.py's CELERY_* comment) - CreateSongAPIView just
validates the project and enqueues create_duet_song, returning
immediately; the frontend gets the actual result over a WebSocket (see
backend.main_app.consumers.DuetProjectStatusConsumer) once this
finishes.
"""
import logging

from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


def duet_status_group(project_id):
    return f'duet_project_{project_id}_status'


def _broadcast_duet_status(project_id, status, error='', redirect_url=None, progress=None):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    async_to_sync(channel_layer.group_send)(duet_status_group(project_id), {
        'type': 'project.status',
        'status': status,
        'error': error,
        'redirect_url': redirect_url,
        'progress': progress,
    })


@shared_task(ignore_result=True)
def send_daily_guess_reminders():
    """Daily nudge (see config/celery.py's beat schedule) to every
    subscribed user who hasn't played today's "خمّن الأغنية" round yet -
    skips anyone who already has (whether they won or lost), and anyone
    with no push subscription at all is never queried for in the first
    place.
    """
    from django.utils import timezone

    from backend.main_app.models import PushSubscription, UserAccount
    from backend.main_app.shared_utils.push_notifications import send_push_to_user
    from backend.music_app.models import DailyGuessAttempt

    today = timezone.localdate()
    already_played = DailyGuessAttempt.objects.filter(challenge__date=today).values_list('user_id', flat=True)
    pending_user_ids = (
        PushSubscription.objects.exclude(user=None)
        .exclude(user_id__in=already_played)
        .values_list('user_id', flat=True)
        .distinct()
    )
    for user in UserAccount.objects.filter(pk__in=pending_user_ids):
        send_push_to_user(
            user, 'خمّن الأغنية 🎧', 'أغنية النهاردة لسه مستنياك - جرب تخمنها!', url='/guess/',
        )


# A duet mix runs Demucs (GPU/CPU-heavy) plus librosa mixing - genuinely
# slow, and worth retrying automatically rather than dumping the whole
# job on the user as a hard failure the moment anything hiccups (a
# transient ffmpeg error, a momentary DB blip, the worker getting
# recycled mid-task). Capped, with backoff, so a truly broken input
# (corrupt audio, missing file) still ends in FAILED instead of retrying
# forever.
DUET_TASK_MAX_RETRIES = 5
DUET_TASK_RETRY_COUNTDOWN = 30

# How stale an InstrumentalVersion's "PROCESSING" can be before we treat
# whichever worker claimed it as dead (crashed, OOM-killed, force-
# restarted) rather than still genuinely working - past this, a new
# attempt is allowed to reclaim and redo it instead of waiting forever
# for a worker that's never coming back.
INSTRUMENTAL_STALE_MINUTES = 20


class _InstrumentalBusyElsewhere(Exception):
    """Another task is already separating this exact song's vocals right
    now - raised so the caller retries later instead of running Demucs
    twice for the same song at the same time.
    """


def _set_duet_progress(project_id, percent):
    """Persists progress and pushes it live over the duet's WebSocket
    group - update() (not save()) so this never fights the in-memory
    `project` object the caller is still holding, and touches updated_at
    itself so the stale-job sweep below can tell "still actively
    progressing" apart from "stuck".
    """
    from django.utils import timezone

    from backend.music_app.models import SingWithTamerProject

    SingWithTamerProject.objects.filter(pk=project_id).update(
        progress_percent=percent, updated_at=timezone.now(),
    )
    _broadcast_duet_status(
        project_id, SingWithTamerProject.ProcessingStatus.PROCESSING, progress=percent,
    )


def _claim_or_wait_for_instrumental(song):
    """Returns the song's ready-to-use InstrumentalVersion, doing the
    (slow) vocal removal itself only if nobody else already has it in
    hand - two duets started for the same song around the same time
    would otherwise both pay for a full Demucs pass instead of the
    second one just reusing the first's result.
    """
    from datetime import timedelta

    from django.db import transaction
    from django.utils import timezone

    from backend.music_app.models import InstrumentalVersion

    with transaction.atomic():
        instrumental, _created = InstrumentalVersion.objects.select_for_update().get_or_create(
            song=song, defaults={'status': InstrumentalVersion.ProcessingStatus.PENDING},
        )

        if instrumental.status == InstrumentalVersion.ProcessingStatus.COMPLETED:
            return instrumental, False

        is_stale = (
            instrumental.status == InstrumentalVersion.ProcessingStatus.PROCESSING
            and timezone.now() - instrumental.updated_at > timedelta(minutes=INSTRUMENTAL_STALE_MINUTES)
        )

        if instrumental.status == InstrumentalVersion.ProcessingStatus.PROCESSING and not is_stale:
            raise _InstrumentalBusyElsewhere()

        instrumental.status = InstrumentalVersion.ProcessingStatus.PROCESSING
        instrumental.processing_error = ''
        instrumental.save(update_fields=['status', 'processing_error', 'updated_at'])
        return instrumental, True


@shared_task(
    bind=True, ignore_result=True, max_retries=DUET_TASK_MAX_RETRIES,
    # A deploy restarting this worker mid-task (see .github/workflows -
    # every push does an unconditional `systemctl restart`) used to just
    # silently lose whatever was running: the default early-ack means
    # the broker already considers the message done the moment it was
    # *handed to* this worker, long before the mix/render actually
    # finishes, so a SIGTERM kill here never gets a chance to redeliver
    # it - only the 20-minute requeue_stuck_duet_projects sweep above
    # would eventually catch it. acks_late + reject_on_worker_lost make
    # Redis redeliver the task immediately once the worker dies, so the
    # freshly-restarted worker just picks it back up and reruns it.
    acks_late=True, reject_on_worker_lost=True,
)
def create_duet_song(self, project_id):
    from backend.music_app.models import InstrumentalVersion, SingWithTamerProject

    try:
        project = SingWithTamerProject.objects.select_related('song').get(pk=project_id)
    except SingWithTamerProject.DoesNotExist:
        return

    try:
        from backend.music_app.core.song_mixer import SongMixer
        from backend.music_app.core.vocal_remover import VocalRemover

        song = project.song

        _set_duet_progress(project_id, 5)

        try:
            instrumental, needs_separation = _claim_or_wait_for_instrumental(song)
        except _InstrumentalBusyElsewhere:
            logger.info(
                'Duet %s waiting on an in-progress instrumental for song %s', project_id, song.pk,
            )
            raise self.retry(countdown=DUET_TASK_RETRY_COUNTDOWN)

        if needs_separation:
            _set_duet_progress(project_id, 15)
            try:
                vocal_remover = VocalRemover()
                instrumental_path = vocal_remover.remove_vocals(song.audio_file.path)
                instrumental.instrumental_file.name = instrumental_path
                instrumental.status = InstrumentalVersion.ProcessingStatus.COMPLETED
                # Quality score not set - Spleeter provides AI-based separation
                instrumental.save()
            except Exception as e:
                instrumental.status = InstrumentalVersion.ProcessingStatus.FAILED
                instrumental.processing_error = str(e)
                instrumental.save()
                raise
            _set_duet_progress(project_id, 55)
        else:
            _set_duet_progress(project_id, 55)

        _set_duet_progress(project_id, 65)
        mixer = SongMixer()
        final_song_path = mixer.create_final_song(
            project, instrumental.instrumental_file.path, song.audio_file.path,
        )
        _set_duet_progress(project_id, 90)

        # Store the mixed duet directly on the project. This is
        # intentionally NOT a catalog Song: it must never show up in
        # song browsing, search, or the admin song list - it's private
        # to this user, visible only on their own "My Duets" page (same
        # as their liked songs).
        project.final_audio_file.name = final_song_path
        project.is_completed = True
        project.processing_status = SingWithTamerProject.ProcessingStatus.COMPLETED
        project.processing_error = ''
        project.progress_percent = 100
        project.save()

        from backend.main_app.shared_utils.gamification import POINTS_DUET_COMPLETED, award_points
        award_points(project.user, POINTS_DUET_COMPLETED)

        # The per-line takes are already baked into final_audio_file
        # above and are never read again - delete them to stop the
        # server disk from filling up with duplicate audio.
        for recording in project.lyric_recordings.all():
            recording.audio_file.delete(save=False)
        project.lyric_recordings.all().delete()

        _broadcast_duet_status(project_id, SingWithTamerProject.ProcessingStatus.COMPLETED, redirect_url='/my-duets/')

    except Exception as e:
        # celery.exceptions.Retry (raised by self.retry() above, both
        # for _InstrumentalBusyElsewhere and for the generic retry path
        # just below) is itself an Exception - let it propagate to
        # Celery untouched instead of being caught here and wrongly
        # marked FAILED. MaxRetriesExceededError (self.retry() giving up
        # after DUET_TASK_MAX_RETRIES attempts of waiting on another
        # worker's instrumental) is a genuine terminal failure and falls
        # through to the FAILED branch below like any other exception.
        from celery.exceptions import Retry
        if isinstance(e, Retry):
            raise

        if self.request.retries < self.max_retries:
            logger.warning(
                'create_duet_song(%s) failed (attempt %s/%s), retrying: %s',
                project_id, self.request.retries + 1, self.max_retries, e,
            )
            raise self.retry(exc=e, countdown=DUET_TASK_RETRY_COUNTDOWN * (self.request.retries + 1))

        project.processing_status = SingWithTamerProject.ProcessingStatus.FAILED
        project.processing_error = str(e)
        project.progress_percent = 0
        project.save(update_fields=['processing_status', 'processing_error', 'progress_percent'])
        _broadcast_duet_status(project_id, SingWithTamerProject.ProcessingStatus.FAILED, error=str(e))


@shared_task(ignore_result=True)
def requeue_stuck_duet_projects():
    """Safety net for a duet (or its video) that got stranded in
    PROCESSING with no task actually running anymore - a worker that
    got SIGKILLed (OOM, deploy restart, host reboot) mid-task never
    reaches its own except block, so nothing else would ever retry it.
    Runs periodically (see config/celery.py's beat schedule) and
    re-enqueues anything that hasn't reported progress in a while.
    """
    from datetime import timedelta

    from django.utils import timezone

    from backend.music_app.models import SingWithTamerProject

    stale_before = timezone.now() - timedelta(minutes=INSTRUMENTAL_STALE_MINUTES)

    stuck = SingWithTamerProject.objects.filter(
        processing_status=SingWithTamerProject.ProcessingStatus.PROCESSING,
        updated_at__lt=stale_before,
    )
    for project in stuck:
        logger.warning('Re-queuing stuck duet project %s (stale since %s)', project.pk, project.updated_at)
        create_duet_song.delay(project.pk)

    stuck_videos = SingWithTamerProject.objects.filter(
        video_status=SingWithTamerProject.ProcessingStatus.PROCESSING,
        updated_at__lt=stale_before,
    )
    for project in stuck_videos:
        logger.warning('Re-queuing stuck duet video %s (stale since %s)', project.pk, project.updated_at)
        create_duet_video.delay(project.pk)


VIDEO_TASK_MAX_RETRIES = 2
VIDEO_TASK_RETRY_COUNTDOWN = 20


def duet_video_status_group(project_id):
    return f'duet_video_{project_id}_status'


def _broadcast_duet_video_status(project_id, status, error='', video_url=None, progress=None):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    async_to_sync(channel_layer.group_send)(duet_video_status_group(project_id), {
        'type': 'video.status',
        'status': status,
        'error': error,
        'video_url': video_url,
        'progress': progress,
    })


def _set_duet_video_progress(project_id, percent):
    """Mirrors _set_duet_progress above, for the video render's own
    ffmpeg-reported percentage (see DuetVideoMaker._run_with_progress) -
    update() so it never fights the `project` object the task is still
    holding. Also touches updated_at (not automatic on a plain
    .update()) so requeue_stuck_duet_projects' staleness check below
    can tell "still actively rendering" apart from "worker got killed
    mid-task and nothing is coming".
    """
    from django.utils import timezone

    from backend.music_app.models import SingWithTamerProject

    SingWithTamerProject.objects.filter(pk=project_id).update(
        video_progress_percent=percent, updated_at=timezone.now(),
    )
    _broadcast_duet_video_status(
        project_id, SingWithTamerProject.ProcessingStatus.PROCESSING, progress=percent,
    )


@shared_task(
    bind=True, ignore_result=True, max_retries=VIDEO_TASK_MAX_RETRIES,
    # See create_duet_song's own acks_late comment above - the exact
    # same failure mode (a deploy's unconditional worker restart killing
    # an in-flight render) is what left duet #21's video stuck at
    # PROCESSING/0% for 10 days with nothing ever retrying it.
    acks_late=True, reject_on_worker_lost=True,
)
def create_duet_video(self, project_id):
    """Renders the optional shareable vertical video for an already-
    completed duet (backend.music_app.core.duet_video_maker) - separate
    from create_duet_song above since most duets never have this asked
    for. The frontend gets live progress and the final result over a
    WebSocket (see backend.main_app.consumers.DuetVideoStatusConsumer)
    instead of polling, same reasoning as create_duet_song's own socket.
    """
    from backend.music_app.models import SingWithTamerProject

    try:
        project = SingWithTamerProject.objects.select_related('song', 'user').get(pk=project_id)
    except SingWithTamerProject.DoesNotExist:
        return

    if not project.is_completed or not project.final_audio_file:
        project.video_status = SingWithTamerProject.ProcessingStatus.FAILED
        project.video_error = 'الدويتو نفسه لسه مش جاهز.'
        project.save(update_fields=['video_status', 'video_error'])
        _broadcast_duet_video_status(project_id, project.video_status, error=project.video_error)
        return

    _set_duet_video_progress(project_id, 0)

    try:
        from backend.music_app.core.duet_video_maker import DuetVideoMaker

        video_path = DuetVideoMaker().create_video(
            project, progress_callback=lambda percent: _set_duet_video_progress(project_id, percent),
        )

        project.video_file.name = video_path
        project.video_status = SingWithTamerProject.ProcessingStatus.COMPLETED
        project.video_error = ''
        project.video_progress_percent = 0
        project.save(update_fields=['video_file', 'video_status', 'video_error', 'video_progress_percent'])
        _broadcast_duet_video_status(project_id, project.video_status, video_url=project.video_file.url)

    except Exception as e:
        if self.request.retries < self.max_retries:
            logger.warning(
                'create_duet_video(%s) failed (attempt %s/%s), retrying: %s',
                project_id, self.request.retries + 1, self.max_retries, e,
            )
            raise self.retry(exc=e, countdown=VIDEO_TASK_RETRY_COUNTDOWN)

        logger.error('create_duet_video(%s) failed permanently: %s', project_id, e)
        project.video_status = SingWithTamerProject.ProcessingStatus.FAILED
        project.video_error = str(e)
        project.video_progress_percent = 0
        project.save(update_fields=['video_status', 'video_error', 'video_progress_percent'])
        _broadcast_duet_video_status(project_id, project.video_status, error=project.video_error)


DUET_VIDEO_RETENTION_HOURS = 24


@shared_task(ignore_result=True)
def cleanup_expired_duet_videos():
    """Deletes a duet's shareable video (and resets it back to
    "not generated") DUET_VIDEO_RETENTION_HOURS after it finished - it's
    an on-demand extra, not the duet itself (final_audio_file lives on
    regardless), and disk isn't infinite; anyone who still wants it can
    just re-generate it from the duet's own detail page. Runs
    periodically (see config/celery.py's beat schedule).
    """
    from datetime import timedelta

    from django.utils import timezone

    from backend.music_app.models import SingWithTamerProject

    expired_before = timezone.now() - timedelta(hours=DUET_VIDEO_RETENTION_HOURS)
    expired = SingWithTamerProject.objects.filter(
        video_status=SingWithTamerProject.ProcessingStatus.COMPLETED,
        updated_at__lt=expired_before,
    ).exclude(video_file='')

    for project in expired:
        logger.info('Deleting expired duet video for project %s (completed %s)', project.pk, project.updated_at)
        project.video_file.delete(save=False)
        project.video_status = SingWithTamerProject.ProcessingStatus.NOT_STARTED
        project.video_progress_percent = 0
        project.save(update_fields=['video_file', 'video_status', 'video_progress_percent'])


@shared_task(ignore_result=True)
def classify_song_task(song_id):
    """Auto-fills a song's genre/mood via an LLM call (see
    backend.music_app.shared_utils.song_classification) - run as a task
    (see music_app.signals) so a dashboard save or an import command
    doesn't block on a network call to an LLM provider. A no-op if the
    song already has both set, or no LLM provider is configured.
    """
    from backend.music_app.models import Song
    from backend.music_app.shared_utils.song_classification import classify_and_save

    song = Song.objects.filter(pk=song_id).first()
    if song:
        classify_and_save(song)
