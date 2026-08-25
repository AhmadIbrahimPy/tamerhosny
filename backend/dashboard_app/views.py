from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from backend.concerts_app.models import Concert
from backend.links_app.models import Platform
from backend.main_app.models import UserAccount
from backend.media_app.models import Media
from backend.music_app.models import Album, Song
from backend.people_app.models import Person
from backend.studios_app.models import Studio


def dashboard_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard_app:home')

    error = None
    if request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST.get('username'),
            password=request.POST.get('password'),
        )
        if user and user.is_active and user.role in UserAccount.DASHBOARD_ROLES:
            auth_login(request, user)
            return redirect('dashboard_app:home')
        error = 'اسم المستخدم أو كلمة المرور غير صحيحة.'

    return render(request, 'dashboard/login.html', {'error': error})


@login_required(login_url='dashboard_app:login')
def dashboard_logout(request):
    auth_logout(request)
    return redirect('dashboard_app:login')


@login_required(login_url='dashboard_app:login')
def home(request):
    stats = {
        'people': Person.objects.count(),
        'studios': Studio.objects.count(),
        'albums': Album.objects.count(),
        'songs': Song.objects.count(),
        'media': Media.objects.count(),
        'concerts': Concert.objects.count(),
    }
    return render(request, 'dashboard/main.html', {'stats': stats})


@login_required(login_url='dashboard_app:login')
def people_list(request):
    return render(request, 'dashboard/pages/people/all.html', {'people': Person.objects.all()})


@login_required(login_url='dashboard_app:login')
def studios_list(request):
    return render(request, 'dashboard/pages/studios/all.html', {'studios': Studio.objects.all()})


@login_required(login_url='dashboard_app:login')
def albums_list(request):
    return render(request, 'dashboard/pages/albums/all.html', {'albums': Album.objects.select_related('record_label')})


@login_required(login_url='dashboard_app:login')
def songs_list(request):
    songs = Song.objects.select_related('album', 'recording_studio', 'related_media')
    return render(request, 'dashboard/pages/songs/all.html', {'songs': songs})


@login_required(login_url='dashboard_app:login')
def media_list(request):
    return render(request, 'dashboard/pages/media/all.html', {'media_items': Media.objects.all()})


@login_required(login_url='dashboard_app:login')
def concerts_list(request):
    return render(request, 'dashboard/pages/concerts/all.html', {'concerts': Concert.objects.select_related('organizer')})


@login_required(login_url='dashboard_app:login')
def platforms_list(request):
    return render(request, 'dashboard/pages/platforms/all.html', {'platforms': Platform.objects.all()})


@login_required(login_url='dashboard_app:login')
def users_list(request):
    return render(request, 'dashboard/pages/users/all.html', {'accounts': UserAccount.objects.all()})
