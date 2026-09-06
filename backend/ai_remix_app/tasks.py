"""Celery tasks for the AI Remix app.

quick_remix (backend.ai_remix_app.api.views) used to run the actual
generation - Demucs-based separation + mixing, both slow - inline in the
request/response cycle. On a real deploy behind nginx that routinely blew
past the gateway timeout (504), even though the work itself eventually
succeeded server-side. This task moves that work to the background the
same way backend.music_app.tasks.create_duet_song already does for
"Sing With Tamer" - the view just creates the project/sources rows and
enqueues this, returning immediately.
"""
import os

from celery import shared_task
from django.conf import settings


@shared_task(bind=True, ignore_result=True)
def generate_quick_remix(self, project_id):
    from backend.ai_remix_app.models import RemixOutput, RemixProject
    from backend.ai_remix_app.core.audio_processor import AIRemixGenerator

    try:
        project = RemixProject.objects.prefetch_related('sources__audio_source').get(pk=project_id)
    except RemixProject.DoesNotExist:
        return

    try:
        sources = list(project.sources.select_related('audio_source').order_by('order'))
        if len(sources) < 2:
            raise ValueError('Remix project is missing its audio sources.')

        generator = AIRemixGenerator()

        sources_data = [
            {
                'file_path': remix_source.audio_source.audio_file.path,
                'volume': 1.0,
                'fade_in': 0.0,
                'fade_out': 0.0,
            }
            for remix_source in sources
        ]

        target_config = {
            'target_bpm': None,
            'target_key': None,
            'effects': {
                'compressor': True,
                'limiter': True,
            },
        }

        remix_audio = generator.generate_remix(sources_data, target_config)

        import uuid

        output_filename = f"quick_remix_{uuid.uuid4().hex}.wav"
        output_path = os.path.join(settings.MEDIA_ROOT, 'ai_remix', 'outputs', output_filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        generator.processor.save_audio(remix_audio, output_path, format='wav')

        RemixOutput.objects.create(
            project=project,
            output_file=f'ai_remix/outputs/{output_filename}',
            format='wav',
            duration=len(remix_audio) / generator.processor.sample_rate,
            file_size=os.path.getsize(output_path),
        )

        project.status = RemixProject.Status.COMPLETED
        project.error_message = ''
        project.save(update_fields=['status', 'error_message', 'updated_at'])

    except Exception as e:
        project.status = RemixProject.Status.FAILED
        project.error_message = str(e)
        project.save(update_fields=['status', 'error_message', 'updated_at'])
