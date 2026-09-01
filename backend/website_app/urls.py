from django.urls import path

from backend.website_app import views

app_name = 'website_app'

urlpatterns = [
    path('', views.home, name='home'),

    path('player/', views.player_page, name='player'),
    path('player/song-data/', views.song_player_data, name='song-player-data'),

    path('people/', views.people_list, name='people'),
    path('people/<str:slug>/', views.person_detail, name='person-detail'),

    path('songs/', views.songs_list, name='songs'),
    path('songs/increment-play/', views.increment_play_count, name='increment-play-count'),
    path('songs/start-listening/', views.start_listening, name='start-listening'),
    path('songs/stop-listening/', views.stop_listening, name='stop-listening'),
    path('songs/listening-heartbeat/', views.listening_heartbeat, name='listening-heartbeat'),
    path('songs/current-listeners/', views.get_current_listeners, name='current-listeners'),
    path('songs/<str:slug>/', views.song_detail, name='song-detail'),

    path('albums/', views.albums_list, name='albums'),
    path('albums/<str:slug>/', views.album_detail, name='album-detail'),

    path('movies/', views.movies_list, name='movies'),
    path('series/', views.series_list, name='series'),
    path('commercials/', views.commercials_list, name='commercials'),
    path('media/<str:slug>/', views.media_detail, name='media-detail'),

    path('concerts/', views.concerts_list, name='concerts'),
    path('concerts/<str:slug>/', views.concert_detail, name='concert-detail'),

    path('remix-result/<int:remix_id>/', views.remix_result, name='remix-result'),

    # User Features
    path('likes/', views.likes_list, name='likes'),
    path('likes/toggle/', views.toggle_favorite, name='toggle-like'),
    path('recently-played/', views.recently_played, name='recently-played'),
    path('playlists/list/', views.list_playlists, name='list-playlists'),
    path('playlists/add-song/', views.add_song_to_playlist, name='add-song-to-playlist'),
    path('playlists/create-with-song/', views.create_playlist_with_song, name='create-playlist-with-song'),
    path('playlists/create/', views.create_playlist, name='create-playlist'),
    path('playlists/', views.playlists_list, name='playlists'),
    path('playlists/<int:pk>/update/', views.update_playlist, name='update-playlist'),
    path('playlists/<int:pk>/remove-song/', views.remove_song_from_playlist, name='remove-song-from-playlist'),
    path('playlists/<int:pk>/', views.playlist_detail, name='playlist-detail'),
    path('remixes/', views.remixes_list, name='remixes'),
]
