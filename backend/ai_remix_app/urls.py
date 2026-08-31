from django.urls import path, include
from rest_framework.routers import DefaultRouter
from backend.ai_remix_app.api.views import (
    AudioSourceViewSet, RemixProjectViewSet, RemixSourceViewSet,
    RemixOutputViewSet, AIModelViewSet, quick_remix
)

router = DefaultRouter()
router.register(r'audio-sources', AudioSourceViewSet, basename='audio-source')
router.register(r'remix-projects', RemixProjectViewSet, basename='remix-project')
router.register(r'remix-sources', RemixSourceViewSet, basename='remix-source')
router.register(r'remix-outputs', RemixOutputViewSet, basename='remix-output')
router.register(r'ai-models', AIModelViewSet, basename='ai-model')

urlpatterns = [
    path('', include(router.urls)),
    path('quick-remix/', quick_remix, name='quick-remix'),
]
