from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404

from backend.main_app.shared_utils.authentication_manager import UserAuthenticationManager
from backend.music_app.core.songs import SongsHandle
from backend.music_app.models import Song, SingWithTamerProject, LyricRecording, SongLyricSegment


@method_decorator(csrf_exempt, name='dispatch')
class SongsLyricsSegmentsAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk, **kwargs):
        song = get_object_or_404(Song, pk=pk)
        segments = song.lyric_segments.all().values(
            'pk', 'start_seconds', 'end_seconds', 'segment_type', 'text', 'vocal_doubling', 'double_tracking'
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


class SingWithTamerProjectAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [SessionAuthentication]

    def post(self, request, **kwargs):
        print(f"User: {request.user}, Authenticated: {request.user.is_authenticated}")
        user = request.user
        song_id = request.POST.get('song_id')
        division_type = request.POST.get('division_type', 'EVEN')

        if not song_id:
            return Response({
                'status': 'error',
                'message': 'Missing required field: song_id'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            song = get_object_or_404(Song, pk=song_id)

            # Create or get project
            project, created = SingWithTamerProject.objects.get_or_create(
                user=user,
                song=song,
                division_type=division_type,
                defaults={'is_completed': False}
            )

            return Response({
                'status': 'success',
                'message': 'Project created/retrieved successfully',
                'data': {
                    'project_id': project.pk,
                    'created': created,
                    'division_type': project.division_type,
                    'is_completed': project.is_completed
                }
            }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request, song_id, **kwargs):
        user = request.user
        song = get_object_or_404(Song, pk=song_id)
        division_type = request.GET.get('division_type', 'EVEN')

        try:
            project = SingWithTamerProject.objects.get(
                user=user,
                song=song,
                division_type=division_type
            )

            # Get all recordings for this project
            recordings = project.lyric_recordings.select_related('lyric_segment').values(
                'pk', 'lyric_segment__pk', 'lyric_segment__text',
                'lyric_segment__start_seconds', 'lyric_segment__end_seconds',
                'audio_file', 'duration_seconds', 'recorded_at'
            )

            return Response({
                'status': 'success',
                'data': {
                    'project_id': project.pk,
                    'division_type': project.division_type,
                    'is_completed': project.is_completed,
                    'recordings': list(recordings)
                }
            }, status=status.HTTP_200_OK)

        except SingWithTamerProject.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Project not found'
            }, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, song_id, **kwargs):
        user = request.user
        song = get_object_or_404(Song, pk=song_id)
        division_type = request.GET.get('division_type', 'EVEN')

        try:
            project = SingWithTamerProject.objects.get(
                user=user,
                song=song,
                division_type=division_type
            )
            
            # Delete all recordings for this project
            project.lyric_recordings.all().delete()
            
            # Delete the project
            project.delete()

            return Response({
                'status': 'success',
                'message': 'Project deleted successfully'
            }, status=status.HTTP_200_OK)

        except SingWithTamerProject.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Project not found'
            }, status=status.HTTP_404_NOT_FOUND)


@method_decorator(csrf_exempt, name='dispatch')
class LyricRecordingAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [SessionAuthentication]

    def post(self, request, **kwargs):
        project_id = request.POST.get('project_id')
        lyric_segment_id = request.POST.get('lyric_segment_id')
        audio_file = request.FILES.get('audio_file')
        duration_seconds = request.POST.get('duration_seconds')

        if not all([project_id, lyric_segment_id, audio_file, duration_seconds]):
            return Response({
                'status': 'error',
                'message': 'Missing required fields: project_id, lyric_segment_id, audio_file, duration_seconds'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            project = get_object_or_404(SingWithTamerProject, pk=project_id, user=request.user)
            lyric_segment = get_object_or_404(SongLyricSegment, pk=lyric_segment_id, song=project.song)

            # Create or update the recording
            recording, created = LyricRecording.objects.update_or_create(
                project=project,
                lyric_segment=lyric_segment,
                defaults={
                    'audio_file': audio_file,
                    'duration_seconds': int(duration_seconds)
                }
            )

            return Response({
                'status': 'success',
                'message': 'Recording saved successfully',
                'data': {
                    'recording_id': recording.pk,
                    'created': created
                }
            }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
class CreateSongAPIView(APIView):
    """Kicks off the duet mix (vocal removal + mixing, both slow) as a
    Celery background task (backend.music_app.tasks.create_duet_song)
    instead of running it inline - returns immediately with a
    "processing" status; the frontend gets the real result over
    /ws/duets/<project_id>/status/ once the task finishes.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [SessionAuthentication]

    def post(self, request, **kwargs):
        from backend.music_app.tasks import create_duet_song

        project_id = request.POST.get('project_id')

        if not project_id:
            return Response({
                'status': 'error',
                'message': 'Missing required field: project_id'
            }, status=status.HTTP_400_BAD_REQUEST)

        project = get_object_or_404(SingWithTamerProject, pk=project_id, user=request.user)

        if project.processing_status == SingWithTamerProject.ProcessingStatus.PROCESSING:
            return Response({
                'status': 'success',
                'message': 'Already processing',
                'data': {'project_id': project.pk, 'processing_status': project.processing_status},
            }, status=status.HTTP_202_ACCEPTED)

        project.processing_status = SingWithTamerProject.ProcessingStatus.PROCESSING
        project.processing_error = ''
        project.save(update_fields=['processing_status', 'processing_error'])

        create_duet_song.delay(project.pk)

        return Response({
            'status': 'success',
            'message': 'Processing started',
            'data': {'project_id': project.pk, 'processing_status': project.processing_status},
        }, status=status.HTTP_202_ACCEPTED)
