from django.urls import path

from backend.music_app.api.albums import AlbumsAPIView
from backend.music_app.api.songs import SongsAPIView

app_name = 'music_app'

urlpatterns = [
    path('albums/', AlbumsAPIView.as_view(), name='albums'),
    path('albums/<int:pk>/', AlbumsAPIView.as_view(), name='album-detail'),
    path('songs/', SongsAPIView.as_view(), name='songs'),
    path('songs/<int:pk>/', SongsAPIView.as_view(), name='song-detail'),
]
