from django.urls import path

from backend.analytics_app.api.track import TrackAPIView

app_name = 'analytics_app'

urlpatterns = [
    path('track/', TrackAPIView.as_view(), name='track'),
]
