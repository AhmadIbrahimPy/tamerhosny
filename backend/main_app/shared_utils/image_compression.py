"""Shrinks every image uploaded anywhere in the dashboard before it's
written to disk, so poster/cover/logo uploads don't eat server storage.

Hooked in generically via a `pre_save` signal (see `apps.py`) instead of
per-model, so it applies to every current and future ImageField across
every app without needing to touch each model.
"""
import io

from django.core.files.uploadedfile import InMemoryUploadedFile, UploadedFile
from django.db.models import ImageField
from PIL import Image, ImageOps

MAX_DIMENSION = 1920
JPEG_QUALITY = 82
PNG_TRANSPARENCY_FORMATS = {'PNG', 'GIF', 'WEBP'}


def compress_uploaded_images(instance):
    """Replaces any freshly-uploaded ImageField value on `instance` with a
    resized, re-encoded version. Already-stored images (loaded back from
    disk, not newly uploaded) are left untouched.
    """
    for field in instance._meta.get_fields():
        if not isinstance(field, ImageField):
            continue
        file_field = getattr(instance, field.attname)
        if not file_field:
            continue
        uploaded_file = file_field.file
        if not isinstance(uploaded_file, UploadedFile):
            continue

        compressed = _compress(file_field)
        if compressed is not None:
            file_field.save(compressed.name, compressed, save=False)


def _compress(file_field):
    try:
        file_field.seek(0)
        image = Image.open(file_field)
        image = ImageOps.exif_transpose(image)
        original_format = (image.format or 'JPEG').upper()
    except Exception:
        return None

    image.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)

    keep_transparency = original_format in PNG_TRANSPARENCY_FORMATS and _has_alpha(image)
    buffer = io.BytesIO()
    if keep_transparency:
        image = image.convert('RGBA')
        image.save(buffer, format='PNG', optimize=True)
        name = _swap_extension(file_field.name, 'png')
        content_type = 'image/png'
    else:
        image = image.convert('RGB')
        image.save(buffer, format='JPEG', quality=JPEG_QUALITY, optimize=True, progressive=True)
        name = _swap_extension(file_field.name, 'jpg')
        content_type = 'image/jpeg'

    buffer.seek(0)
    return InMemoryUploadedFile(
        buffer, None, name, content_type, buffer.getbuffer().nbytes, None,
    )


def _has_alpha(image):
    return image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info)


def _swap_extension(name, extension):
    base = name.rsplit('.', 1)[0] if '.' in name else name
    return f'{base}.{extension}'
