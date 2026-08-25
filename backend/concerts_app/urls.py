from django.urls import path

from backend.concerts_app.api.concerts import ConcertsAPIView

app_name = 'concerts_app'

urlpatterns = [
    path('', ConcertsAPIView.as_view(), name='concerts'),
    path('<int:pk>/', ConcertsAPIView.as_view(), name='concert-detail'),
]
