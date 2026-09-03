from django.apps import AppConfig
from django.db.models.signals import pre_save


class MainAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.main_app'
    label = 'main_app'

    def ready(self):
        from backend.main_app.shared_utils.audio_compression import compress_uploaded_audio
        from backend.main_app.shared_utils.image_compression import compress_uploaded_images
        from backend.main_app.shared_utils.video_compression import compress_uploaded_video

        def _compress_on_save(sender, instance, **kwargs):
            compress_uploaded_images(instance)
            compress_uploaded_audio(instance)
            compress_uploaded_video(instance)

        pre_save.connect(_compress_on_save, dispatch_uid='main_app_compress_uploaded_images')
