from django.urls import path

from backend.studios_app.api.studios import StudiosAPIView

app_name = 'studios_app'

urlpatterns = [
    path('', StudiosAPIView.as_view(), name='studios'),
    path('<int:pk>/', StudiosAPIView.as_view(), name='studio-detail'),
]
