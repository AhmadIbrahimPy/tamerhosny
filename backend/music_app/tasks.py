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


@shared_task(bind=True, ignore_result=True, max_retries=DUET_TASK_MAX_RETRIES)
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
    """Safety net for a duet that got stranded in PROCESSING with no
    task actually running anymore - a worker that got SIGKILLed (OOM,
    deploy, host reboot) mid-task never reaches create_duet_song's own
    except block, so nothing else would ever retry it. Runs periodically
    (see config/celery.py's beat schedule) and re-enqueues anything that
    hasn't reported progress in a while.
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
