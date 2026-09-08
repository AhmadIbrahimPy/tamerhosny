"""Push-notification triggers for new/updated catalog content - see
backend.main_app.shared_utils.push_notifications for how the send
itself works. Kept as signals (not calls inlined into the dashboard
views that do these saves) so any path that publishes a song/album or
adds its first lyrics segment triggers the same notification, whether
that happens from the dashboard, an import command, or anywhere else.
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from backend.main_app.shared_utils.push_notifications import send_push_to_all
from backend.music_app.models import Album, Song, SongLyricSegment


def _capture_old_state(sender, instance, **kwargs):
    """Stashes the DB's current audio_file/visibility on the instance
    before save - a plain post_save only ever sees the new state, so
    there'd be no way to tell "just got published" or "just got its
    first audio file" from "already was that way".
    """
    if not instance.pk:
        instance._push_old_audio_file = ''
        instance._push_old_visibility = None
        return
    old = sender.objects.filter(pk=instance.pk).only('audio_file', 'visibility').first()
    instance._push_old_audio_file = old.audio_file.name if old and old.audio_file else ''
    instance._push_old_visibility = old.visibility if old else None


@receiver(pre_save, sender=Song)
def song_pre_save(sender, instance, **kwargs):
    _capture_old_state(sender, instance, **kwargs)


@receiver(post_save, sender=Song)
def song_post_save(sender, instance, created, **kwargs):
    # Auto-classify genre/mood for a new song (or one still missing
    # either) - see backend.music_app.shared_utils.song_classification.
    # Only worth queuing when there's actually something to fill in;
    # classify_and_save() no-ops anyway, but this skips the task/network
    # round-trip entirely for the common case of an already-tagged song
    # being saved again for something unrelated.
    needs_classification = (
        not instance.genre or instance.genre == instance.Genre.UNSPECIFIED
        or not instance.mood or instance.mood == instance.Mood.UNSPECIFIED
    )
    if needs_classification:
        from backend.music_app.tasks import classify_song_task
        classify_song_task.delay(instance.pk)

    just_published = instance.visibility == instance.Visibility.PUBLISHED and (
        created or instance._push_old_visibility != instance.Visibility.PUBLISHED
    )
    if just_published:
        send_push_to_all('أغنية جديدة 🎵', instance.title_ar, url=f'/songs/{instance.slug}/')
        return

    if instance.visibility != instance.Visibility.PUBLISHED:
        return

    # Audio just got added to a song that was already published without one.
    if not created and instance.audio_file and not instance._push_old_audio_file:
        send_push_to_all(
            'تقدر تسمعها دلوقتي 🎧',
            f'اتضاف ملف صوتي لأغنية "{instance.title_ar}"',
            url=f'/songs/{instance.slug}/',
        )


@receiver(pre_save, sender=Album)
def album_pre_save(sender, instance, **kwargs):
    _capture_old_state(sender, instance, **kwargs)


@receiver(post_save, sender=Album)
def album_post_save(sender, instance, created, **kwargs):
    just_published = instance.visibility == instance.Visibility.PUBLISHED and (
        created or instance._push_old_visibility != instance.Visibility.PUBLISHED
    )
    if just_published:
        send_push_to_all('ألبوم جديد 💿', instance.title_ar, url=f'/albums/{instance.slug}/')


@receiver(post_save, sender=SongLyricSegment)
def lyric_segment_post_save(sender, instance, created, **kwargs):
    if not created:
        return

    song = instance.song
    # A song created without lyrics only got classified from its title
    # (see song_post_save) - re-run now that real lyrics exist, still a
    # no-op if it already has both genre and mood set.
    if not song.genre or song.genre == song.Genre.UNSPECIFIED or not song.mood or song.mood == song.Mood.UNSPECIFIED:
        from backend.music_app.tasks import classify_song_task
        classify_song_task.delay(song.pk)

    # Only the FIRST segment added to a song is worth a push - every
    # segment after that is just the same "it has lyrics now" fact again.
    if song.visibility != song.Visibility.PUBLISHED:
        return
    if song.lyric_segments.count() == 1:
        send_push_to_all(
            'الكلمات اتضافت 📝',
            f'دلوقتي تقدر تتابع كلمات أغنية "{song.title_ar}"',
            url=f'/songs/{song.slug}/',
        )
