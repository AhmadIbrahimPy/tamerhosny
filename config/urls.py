from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from backend.filmography_app import urls as urls_filmography_app
from backend.main_app import urls as urls_main_app
from backend.music_app import urls as urls_music_app
from backend.people_app import urls as urls_people_app

# <version>/ is captured by DRF's URLPathVersioning (see REST_FRAMEWORK
# settings) — one path prefix per app, no nesting app URLs into each other.
urlpatterns = [
    path(f'{settings.ADMIN_URL_PATH}/', admin.site.urls),
    path('<str:version>/main/', include((urls_main_app, 'main_app'))),
    path('<str:version>/people/', include((urls_people_app, 'people_app'))),
    path('<str:version>/music/', include((urls_music_app, 'music_app'))),
    path('<str:version>/filmography/', include((urls_filmography_app, 'filmography_app'))),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
