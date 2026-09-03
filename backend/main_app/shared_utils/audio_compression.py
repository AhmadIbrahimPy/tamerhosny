"""Shrinks newly-uploaded audio files (dashboard song/instrumental
uploads, etc.) before they're written to disk, without audibly hurting
quality: lossless/very-high-bitrate sources are transcoded down to a
high-quality constant bitrate; anything already reasonably compressed is
left untouched rather than re-encoded (re-encoding lossy audio twice
loses quality for little extra size gain).

Hooked in generically via the same `pre_save` signal as image
compression (see `apps.py`), scoped to FileFields whose uploaded
filename has an audio extension - so it does not touch `cover_video`.
"""
import shutil
import subprocess
import tempfile
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.db.models import FileField

AUDIO_EXTENSIONS = {'.wav', '.aiff', '.aif', '.flac', '.mp3', '.m4a', '.aac', '.ogg', '.wma'}
LOSSLESS_EXTENSIONS = {'.wav', '.aiff', '.aif', '.flac'}
TARGET_BITRATE = '192k'
# Below this, re-encoding a lossy file isn't worth the extra generation loss.
SKIP_REENCODE_BITRATE = 200_000

FFMPEG = shutil.which('ffmpeg')
FFPROBE = shutil.which('ffprobe')


def compress_uploaded_audio(instance):
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
        if extension not in AUDIO_EXTENSIONS:
            continue

        compressed = _compress(file_field, extension)
        if compressed is not None:
            new_name = str(Path(file_field.name).with_suffix('.m4a'))
            file_field.save(new_name, compressed, save=False)


def _compress(file_field, extension):
    file_field.seek(0)
    data = file_field.read()

    with tempfile.TemporaryDirectory() as tmp_dir:
        source_path = Path(tmp_dir) / f'source{extension}'
        source_path.write_bytes(data)

        if extension not in LOSSLESS_EXTENSIONS and not _bitrate_worth_reencoding(source_path):
            return None

        output_path = Path(tmp_dir) / 'output.m4a'
        result = subprocess.run(
            [
                FFMPEG, '-y', '-i', str(source_path),
                '-vn', '-c:a', 'aac', '-b:a', TARGET_BITRATE,
                str(output_path),
            ],
            capture_output=True,
        )
        if result.returncode != 0 or not output_path.exists():
            return None

        output_bytes = output_path.read_bytes()

    # Only keep the re-encode if it actually saved meaningful space.
    if len(output_bytes) >= len(data) * 0.95:
        return None
    return ContentFile(output_bytes)


def _bitrate_worth_reencoding(source_path):
    result = subprocess.run(
        [
            FFPROBE, '-v', 'error', '-select_streams', 'a:0',
            '-show_entries', 'stream=bit_rate', '-of', 'default=noprint_wrappers=1:nokey=1',
            str(source_path),
        ],
        capture_output=True, text=True,
    )
    try:
        bitrate = int(result.stdout.strip())
    except ValueError:
        return True
    return bitrate > SKIP_REENCODE_BITRATE
