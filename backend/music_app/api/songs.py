from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404

from backend.main_app.shared_utils.authentication_manager import UserAuthenticationManager
from backend.music_app.core.songs import SongsHandle
from backend.music_app.models import Song


@method_decorator(csrf_exempt, name='dispatch')
class SongsLyricsSegmentsAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk, **kwargs):
        song = get_object_or_404(Song, pk=pk)
        segments = song.lyric_segments.all().values(
            'pk', 'start_seconds', 'end_seconds', 'segment_type', 'text'
        )
        
        segments_list = list(segments)
        
        return Response({
            'status': 'success',
            'results': segments_list
        }, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name='dispatch')
class SongsAPIView(APIView):
    permission_classes = [AllowAny]

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get(self, request, pk=None, **kwargs):
        call_response = SongsHandle(request)
        call_response = call_response.view(pk) if pk else call_response.all()
        
        # Auto-fetch lyrics if segments don't exist (for single song view)
        if pk and call_response[0] == status.HTTP_200_OK:
            from backend.music_app.models import Song
            from backend.music_app.shared_utils.lyrics_fetcher import fetch_and_save_lyrics_for_song
            song = Song.objects.filter(pk=pk).first()
            if song and not song.lyric_segments.exists():
                fetch_and_save_lyrics_for_song(song)
        
        return Response({'details': call_response[1], 'data': call_response[2]}, call_response[0])

    def post(self, request, **kwargs):
        call_response = UserAuthenticationManager(request).handle_logged_in()
        if call_response[0] == status.HTTP_200_OK:
            call_response = SongsHandle(request).create()
        return Response({'details': call_response[1], 'data': call_response[2]}, call_response[0])

    def put(self, request, pk, **kwargs):
        call_response = UserAuthenticationManager(request).handle_logged_in()
        if call_response[0] == status.HTTP_200_OK:
            call_response = SongsHandle(request).update(pk)
        return Response({'details': call_response[1], 'data': call_response[2]}, call_response[0])

    def delete(self, request, pk, **kwargs):
        call_response = UserAuthenticationManager(request).handle_logged_in()
        if call_response[0] == status.HTTP_200_OK:
            call_response = SongsHandle(request).delete(pk)
        return Response({'details': call_response[1], 'data': call_response[2]}, call_response[0])
