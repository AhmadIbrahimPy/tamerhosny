from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from backend.ads_app import urls as urls_ads_app
from backend.ai_remix_app import urls as urls_ai_remix_app
from backend.analytics_app import urls as urls_analytics_app
from backend.concerts_app import urls as urls_concerts_app
from backend.main_app import urls as urls_main_app
from backend.media_app import urls as urls_media_app
from backend.music_app import urls as urls_music_app
from backend.people_app import urls as urls_people_app
from backend.studios_app import urls as urls_studios_app

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path(f'{settings.ADMIN_URL_PATH}/', admin.site.urls),

    # Server-rendered internal dashboard (session auth), on an obfuscated
    # path — never /dashboard/. Must come before the versioned API
    # patterns below, otherwise Django's <str:version> catch-all could
    # swallow a guessed prefix.
    path(f'{settings.DASHBOARD_URL_PATH}/', include('backend.dashboard_app.urls')),

    # JSON API — <version>/ is captured by DRF's URLPathVersioning (see
    # REST_FRAMEWORK settings). One path prefix per app, no nesting.
    path('<str:version>/main/', include((urls_main_app, 'main_app'))),
    path('<str:version>/people/', include((urls_people_app, 'people_app'))),
    path('<str:version>/studios/', include((urls_studios_app, 'studios_app'))),
    path('<str:version>/music/', include((urls_music_app, 'music_app'))),
    path('<str:version>/media/', include((urls_media_app, 'media_app'))),
    path('<str:version>/concerts/', include((urls_concerts_app, 'concerts_app'))),
    path('<str:version>/ads/', include((urls_ads_app, 'ads_app'))),
    path('<str:version>/analytics/', include((urls_analytics_app, 'analytics_app'))),
    path('<str:version>/ai-remix/', include((urls_ai_remix_app, 'ai_remix_app'))),

    # Public website — root path, server-rendered, no auth.
    path('', include('backend.website_app.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
