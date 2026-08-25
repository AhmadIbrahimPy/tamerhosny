from django.urls import path

from backend.people_app.api.people import PeopleAPIView

app_name = 'people_app'

urlpatterns = [
    path('', PeopleAPIView.as_view(), name='people'),
    path('<int:pk>/', PeopleAPIView.as_view(), name='person-detail'),
]
