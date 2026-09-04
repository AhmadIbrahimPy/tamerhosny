"""Celery tasks - currently just the "Sing With Tamer" duet mix.

Vocal removal (AI) + audio mixing is slow enough that running it inside
the request/response cycle would block a whole Daphne process (see
config/settings.py's CELERY_* comment) - CreateSongAPIView just
validates the project and enqueues create_duet_song, returning
immediately; the frontend gets the actual result over a WebSocket (see
backend.main_app.consumers.DuetProjectStatusConsumer) once this
finishes.
"""
from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer


def duet_status_group(project_id):
    return f'duet_project_{project_id}_status'


def _broadcast_duet_status(project_id, status, error='', redirect_url=None):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    async_to_sync(channel_layer.group_send)(duet_status_group(project_id), {
        'type': 'project.status',
        'status': status,
        'error': error,
        'redirect_url': redirect_url,
    })


@shared_task(bind=True, ignore_result=True)
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

        instrumental, _created = InstrumentalVersion.objects.get_or_create(
            song=song, defaults={'status': InstrumentalVersion.ProcessingStatus.PENDING},
        )
        if instrumental.status != InstrumentalVersion.ProcessingStatus.COMPLETED:
            instrumental.status = InstrumentalVersion.ProcessingStatus.PROCESSING
            instrumental.save()
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

        mixer = SongMixer()
        final_song_path = mixer.create_final_song(
            project, instrumental.instrumental_file.path, song.audio_file.path,
        )

        # Store the mixed duet directly on the project. This is
        # intentionally NOT a catalog Song: it must never show up in
        # song browsing, search, or the admin song list - it's private
        # to this user, visible only on their own "My Duets" page (same
        # as their liked songs).
        project.final_audio_file.name = final_song_path
        project.is_completed = True
        project.processing_status = SingWithTamerProject.ProcessingStatus.COMPLETED
        project.processing_error = ''
        project.save()

        # The per-line takes are already baked into final_audio_file
        # above and are never read again - delete them to stop the
        # server disk from filling up with duplicate audio.
        for recording in project.lyric_recordings.all():
            recording.audio_file.delete(save=False)
        project.lyric_recordings.all().delete()

        _broadcast_duet_status(project_id, SingWithTamerProject.ProcessingStatus.COMPLETED, redirect_url='/my-duets/')
    except Exception as e:
        project.processing_status = SingWithTamerProject.ProcessingStatus.FAILED
        project.processing_error = str(e)
        project.save(update_fields=['processing_status', 'processing_error'])
        _broadcast_duet_status(project_id, SingWithTamerProject.ProcessingStatus.FAILED, error=str(e))
