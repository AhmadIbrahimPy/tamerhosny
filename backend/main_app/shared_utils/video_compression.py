"""Shrinks newly-uploaded videos (movie/series/concert hero videos from
the dashboard) before they're written to disk, without visibly hurting
quality: re-encodes to H.264 at a quality level that's effectively
indistinguishable from the source, and skips anything already encoded
efficiently so it isn't needlessly re-compressed and degraded twice.

Hooked in generically via the same `pre_save` signal as image/audio
compression (see `apps.py`), scoped to FileFields whose uploaded
filename has a video extension.
"""
import shutil
import subprocess
import tempfile
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.db.models import FileField

VIDEO_EXTENSIONS = {'.mp4', '.mov', '.mkv', '.avi', '.webm', '.m4v'}
CRF = 23
AUDIO_BITRATE = '128k'
ALREADY_EFFICIENT_CODECS = {'h264', 'hevc', 'vp9', 'av1'}
# Below this the source is already reasonably compressed for its codec -
# re-encoding again would only cost quality for little size gain.
SKIP_REENCODE_BITRATE = 4_000_000

FFMPEG = shutil.which('ffmpeg')
FFPROBE = shutil.which('ffprobe')


def compress_uploaded_video(instance):
    if not FFMPEG or not FFPROBE:
        return

    for field in instance._meta.get_fields():
        if not isinstance(field, FileField):
            continue
        file_field = getattr(instance, field.attname)
        if not file_field:
            continue
        uploaded_file = file_field.file
        if not isinstance(uploaded_file, UploadedFile):
            continue

        extension = Path(file_field.name).suffix.lower()
        if extension not in VIDEO_EXTENSIONS:
            continue

        compressed = _compress(file_field, extension)
        if compressed is not None:
            new_name = str(Path(file_field.name).with_suffix('.mp4'))
            file_field.save(new_name, compressed, save=False)


def _compress(file_field, extension):
    file_field.seek(0)
    data = file_field.read()

    with tempfile.TemporaryDirectory() as tmp_dir:
        source_path = Path(tmp_dir) / f'source{extension}'
        source_path.write_bytes(data)

        if not _worth_reencoding(source_path):
            return None

        output_path = Path(tmp_dir) / 'output.mp4'
        result = subprocess.run(
            [
                FFMPEG, '-y', '-i', str(source_path),
                '-c:v', 'libx264', '-preset', 'faster', '-crf', str(CRF),
                '-c:a', 'aac', '-b:a', AUDIO_BITRATE,
                '-movflags', '+faststart',
                str(output_path),
            ],
            capture_output=True,
        )
        if result.returncode != 0 or not output_path.exists():
            return None

        output_bytes = output_path.read_bytes()

    if len(output_bytes) >= len(data) * 0.95:
        return None
    return ContentFile(output_bytes)


def _worth_reencoding(source_path):
    result = subprocess.run(
        [
            FFPROBE, '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'stream=codec_name,bit_rate', '-of',
            'default=noprint_wrappers=1',
            str(source_path),
        ],
        capture_output=True, text=True,
    )
    info = dict(line.split('=', 1) for line in result.stdout.strip().splitlines() if '=' in line)
    codec = info.get('codec_name', '')
    try:
        bitrate = int(info.get('bit_rate', ''))
    except ValueError:
        bitrate = None

    if codec not in ALREADY_EFFICIENT_CODECS:
        return True
    if bitrate is None:
        return True
    return bitrate > SKIP_REENCODE_BITRATE
