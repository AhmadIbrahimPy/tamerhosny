from django.urls import path

from backend.media_app.api.media import MediaAPIView

app_name = 'media_app'

urlpatterns = [
    path('', MediaAPIView.as_view(), name='media'),
    path('<int:pk>/', MediaAPIView.as_view(), name='media-detail'),
]
