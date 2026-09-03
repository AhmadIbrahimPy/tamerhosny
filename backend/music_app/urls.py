from django.urls import path

from backend.music_app.api.albums import AlbumsAPIView
from backend.music_app.api.songs import SongsAPIView, SongsLyricsSegmentsAPIView, SingWithTamerProjectAPIView, LyricRecordingAPIView, CreateSongAPIView

app_name = 'music_app'

urlpatterns = [
    path('albums/', AlbumsAPIView.as_view(), name='albums'),
    path('albums/<int:pk>/', AlbumsAPIView.as_view(), name='album-detail'),
    path('songs/', SongsAPIView.as_view(), name='songs'),
    path('songs/<int:pk>/', SongsAPIView.as_view(), name='song-detail'),
    path('songs/<int:pk>/lyrics-segments/', SongsLyricsSegmentsAPIView.as_view(), name='song-lyrics-segments'),
    path('sing-with-tamer/projects/', SingWithTamerProjectAPIView.as_view(), name='sing-with-tamer-projects'),
    path('sing-with-tamer/projects/<int:song_id>/', SingWithTamerProjectAPIView.as_view(), name='sing-with-tamer-project'),
    path('sing-with-tamer/recordings/', LyricRecordingAPIView.as_view(), name='lyric-recordings'),
    path('sing-with-tamer/create-song/', CreateSongAPIView.as_view(), name='create-song'),
]
