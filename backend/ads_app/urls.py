from django.urls import path

from backend.ads_app.api.ads import AdsAPIView

app_name = 'ads_app'

urlpatterns = [
    path('', AdsAPIView.as_view(), name='ads'),
    path('<int:pk>/', AdsAPIView.as_view(), name='ad-detail'),
]
