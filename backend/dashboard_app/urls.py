from django.urls import path

from backend.dashboard_app import views

app_name = 'dashboard_app'

urlpatterns = [
    path('login/', views.dashboard_login, name='login'),
    path('logout/', views.dashboard_logout, name='logout'),
    path('', views.home, name='home'),
    path('analytics/', views.analytics_overview, name='analytics'),

    # People
    path('people/', views.people_list, name='people'),
    path('people/create/', views.person_create, name='person-create'),
    path('people/<int:pk>/', views.person_view, name='person-view'),
    path('people/<int:pk>/edit/', views.person_edit, name='person-edit'),
    path('people/<int:pk>/delete/', views.person_delete, name='person-delete'),

    # Studios
    path('studios/', views.studios_list, name='studios'),
    path('studios/create/', views.studio_create, name='studio-create'),
    path('studios/<int:pk>/', views.studio_view, name='studio-view'),
    path('studios/<int:pk>/edit/', views.studio_edit, name='studio-edit'),
    path('studios/<int:pk>/delete/', views.studio_delete, name='studio-delete'),

    # Albums
    path('albums/', views.albums_list, name='albums'),
    path('albums/create/', views.album_create, name='album-create'),
    path('albums/<int:pk>/', views.album_view, name='album-view'),
    path('albums/<int:pk>/edit/', views.album_edit, name='album-edit'),
    path('albums/<int:pk>/delete/', views.album_delete, name='album-delete'),
    path('albums/<int:pk>/toggle/', views.album_toggle_visibility, name='album-toggle'),

    # Songs
    path('songs/', views.songs_list, name='songs'),
    path('songs/create/', views.song_create, name='song-create'),
    path('songs/<int:pk>/', views.song_view, name='song-view'),
    path('songs/<int:pk>/edit/', views.song_edit, name='song-edit'),
    path('songs/<int:pk>/delete/', views.song_delete, name='song-delete'),
    path('songs/<int:pk>/toggle/', views.song_toggle_visibility, name='song-toggle'),
    path('songs/<int:pk>/segments/', views.song_segments, name='song-segments'),
    path('songs/<int:pk>/segments/<int:segment_pk>/edit/', views.song_segment_edit, name='song-segment-edit'),
    path('songs/<int:pk>/segments/<int:segment_pk>/delete/', views.song_segment_delete, name='song-segment-delete'),

    # Media
    path('media/', views.media_list, name='media'),
    path('media/create/', views.media_create, name='media-create'),
    path('media/<int:pk>/', views.media_view, name='media-view'),
    path('media/<int:pk>/edit/', views.media_edit, name='media-edit'),
    path('media/<int:pk>/delete/', views.media_delete, name='media-delete'),
    path('media/<int:pk>/toggle/', views.media_toggle_visibility, name='media-toggle'),

    # Concerts
    path('concerts/', views.concerts_list, name='concerts'),
    path('concerts/create/', views.concert_create, name='concert-create'),
    path('concerts/<int:pk>/', views.concert_view, name='concert-view'),
    path('concerts/<int:pk>/edit/', views.concert_edit, name='concert-edit'),
    path('concerts/<int:pk>/delete/', views.concert_delete, name='concert-delete'),
    path('concerts/<int:pk>/toggle/', views.concert_toggle_visibility, name='concert-toggle'),

    # Platforms
    path('platforms/', views.platforms_list, name='platforms'),
    path('platforms/create/', views.platform_create, name='platform-create'),
    path('platforms/<int:pk>/', views.platform_view, name='platform-view'),
    path('platforms/<int:pk>/edit/', views.platform_edit, name='platform-edit'),
    path('platforms/<int:pk>/delete/', views.platform_delete, name='platform-delete'),

    # Users
    path('users/', views.users_list, name='users'),
    path('users/create/', views.user_create, name='user-create'),
    path('users/<int:pk>/', views.user_view, name='user-view'),
    path('users/<int:pk>/edit/', views.user_edit, name='user-edit'),
    path('users/<int:pk>/delete/', views.user_delete, name='user-delete'),
    path('users/<int:pk>/toggle/', views.user_toggle_active, name='user-toggle'),
]
