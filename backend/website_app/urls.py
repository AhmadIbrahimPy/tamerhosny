from django.urls import path

from backend.website_app import views

app_name = 'website_app'

urlpatterns = [
    path('', views.home, name='home'),

    path('people/', views.people_list, name='people'),
    path('people/<str:slug>/', views.person_detail, name='person-detail'),

    path('songs/', views.songs_list, name='songs'),
    path('songs/<str:slug>/', views.song_detail, name='song-detail'),

    path('albums/', views.albums_list, name='albums'),
    path('albums/<str:slug>/', views.album_detail, name='album-detail'),

    path('movies/', views.movies_list, name='movies'),
    path('series/', views.series_list, name='series'),
    path('commercials/', views.commercials_list, name='commercials'),
    path('media/<str:slug>/', views.media_detail, name='media-detail'),

    path('concerts/', views.concerts_list, name='concerts'),
    path('concerts/<str:slug>/', views.concert_detail, name='concert-detail'),
]
