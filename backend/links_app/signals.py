"""Push notification when a song gets its first platform link - see
backend.main_app.shared_utils.push_notifications for the send itself.
Only songs, not the other content types ExternalLink can point at
(person/album/media/concert), since that's the specific case asked for.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from backend.links_app.models import ExternalLink
from backend.main_app.shared_utils.push_notifications import send_push_to_all


@receiver(post_save, sender=ExternalLink)
def external_link_post_save(sender, instance, created, **kwargs):
    if not created or instance.content_type.model != 'song':
        return

    song = instance.content_object
    if song is None or song.visibility != song.Visibility.PUBLISHED:
        return

    if song.links.count() == 1:
        send_push_to_all(
            'روابط جديدة 🔗',
            f'دلوقتي تقدر تسمع أغنية "{song.title_ar}" من منصات تانية',
            url=f'/songs/{song.slug}/',
        )
