from django.urls import path

from backend.dashboard_app import views

app_name = 'dashboard_app'

urlpatterns = [
    path('login/', views.dashboard_login, name='login'),
    path('logout/', views.dashboard_logout, name='logout'),
    path('', views.home, name='home'),
    path('people/', views.people_list, name='people'),
    path('studios/', views.studios_list, name='studios'),
    path('albums/', views.albums_list, name='albums'),
    path('songs/', views.songs_list, name='songs'),
    path('media/', views.media_list, name='media'),
    path('concerts/', views.concerts_list, name='concerts'),
    path('platforms/', views.platforms_list, name='platforms'),
    path('users/', views.users_list, name='users'),
]
