from django.urls import path

from backend.main_app.api.auth import LoginAPIView, LogoutAPIView, RefreshAPIView
from backend.main_app.api.users import UsersAPIView

app_name = 'main_app'

urlpatterns = [
    path('auth/login/', LoginAPIView.as_view(), name='login'),
    path('auth/refresh/', RefreshAPIView.as_view(), name='refresh'),
    path('auth/logout/', LogoutAPIView.as_view(), name='logout'),
    path('users/', UsersAPIView.as_view(), name='users'),
    path('users/<int:pk>/', UsersAPIView.as_view(), name='user-detail'),
]
