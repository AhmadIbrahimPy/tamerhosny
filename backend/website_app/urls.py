from django.urls import path

from backend.website_app import auth_views, proxy_views, push_views, views

app_name = 'website_app'

urlpatterns = [
    path('', views.home, name='home'),
    path('robots.txt', views.robots_txt, name='robots-txt'),
    path('sw.js', push_views.service_worker, name='service-worker'),
    path('push/subscribe/', push_views.push_subscribe, name='push-subscribe'),
    path('push/unsubscribe/', push_views.push_unsubscribe, name='push-unsubscribe'),
    path('img-proxy/', proxy_views.cover_art_proxy, name='cover-art-proxy'),

    # Public site auth (separate from the internal dashboard login) -
    # JSON endpoints backing the login/register modal.
    path('auth/register/', auth_views.register, name='auth-register'),
    path('auth/login/', auth_views.login_view, name='auth-login'),
    path('auth/logout/', auth_views.logout_view, name='auth-logout'),
    path('auth/forgot-password/request/', auth_views.forgot_password_request, name='auth-forgot-password-request'),
    path('auth/forgot-password/verify/', auth_views.forgot_password_verify, name='auth-forgot-password-verify'),
    path('auth/forgot-password/reset/', auth_views.forgot_password_reset, name='auth-forgot-password-reset'),
    path('auth/google/start/', auth_views.google_login_start, name='auth-google-start'),
    path('auth/google/callback/', auth_views.google_login_callback, name='auth-google-callback'),

    path('tamer-hosny/', views.tamer_bio, name='tamer-bio'),

    path('player/', views.player_page, name='player'),
    path('player/song-data/', views.song_player_data, name='song-player-data'),
    path('player/voice-search/', views.voice_search_songs, name='voice-search-songs'),

    path('people/', views.people_list, name='people'),
    path('people/<str:slug>/', views.person_detail, name='person-detail'),

    path('songs/', views.songs_list, name='songs'),
    path('songs/increment-play/', views.increment_play_count, name='increment-play-count'),
    path('songs/full-listen/', views.record_full_listen, name='record-full-listen'),
    path('songs/<str:slug>/', views.song_detail, name='song-detail'),
    path('songs/<str:slug>/duet/<int:duet_id>/', views.song_detail, name='song-detail-duet'),
    path('sing-with-tamer/<str:slug>/', views.sing_with_tamer, name='sing-with-tamer'),

    path('guess/', views.daily_guess_game, name='daily-guess'),
    path('guess/attempt/', views.daily_guess_attempt, name='daily-guess-attempt'),
    path('guess/track/', views.daily_guess_track, name='daily-guess-track'),
    path('guess/history/', views.daily_guess_history, name='daily-guess-history'),
    path('guess/history/<str:date>/', views.daily_guess_history_day, name='daily-guess-history-day'),

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
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('u/<str:username>/', views.public_profile, name='public-profile'),
    path('u/<str:username>/recap/', views.recap, name='recap'),
    path('u/<str:username>/most-listened/', views.profile_most_listened, name='profile-most-listened'),
    path('u/<str:username>/favorites/', views.profile_favorites, name='profile-favorites'),
    path('profile/update/', views.update_profile, name='update-profile'),

    path('likes/', views.likes_list, name='likes'),
    path('likes/toggle/', views.toggle_favorite, name='toggle-like'),
    path('my-duets/', views.my_duets_list, name='my-duets'),
    path('my-duets/<int:pk>/toggle-privacy/', views.toggle_duet_privacy, name='toggle-duet-privacy'),
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
