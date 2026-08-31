from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny
from django.conf import settings
from django.core.files.storage import default_storage
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from backend.music_app.models import Song
import os
import uuid

from backend.ai_remix_app.models import AudioSource, RemixProject, RemixSource, RemixOutput, AIModel
from backend.ai_remix_app.api.serializers import (
    AudioSourceSerializer, RemixProjectSerializer, RemixSourceSerializer,
    RemixOutputSerializer, AIModelSerializer, RemixRequestSerializer
)
from backend.ai_remix_app.core.audio_processor import AudioProcessor, AIRemixGenerator


class AudioSourceViewSet(viewsets.ModelViewSet):
    """ViewSet لإدارة المصادر الصوتية"""
    queryset = AudioSource.objects.all()
    serializer_class = AudioSourceSerializer
    parser_classes = [MultiPartParser, FormParser]
    
    def perform_create(self, serializer):
        """تحليل الملف الصوتي تلقائياً عند الرفع"""
        audio_file = self.request.FILES.get('audio_file')
        instance = serializer.save()
        
        if audio_file:
            try:
                processor = AudioProcessor()
                file_path = instance.audio_file.path
                audio_data, sr = processor.load_audio(file_path)
                analysis = processor.analyze_audio(audio_data)
                
                # تحديث معلومات الملف
                instance.bpm = int(analysis['bpm'])
                instance.key = analysis['key']
                instance.duration = analysis['duration']
                instance.save()
            except Exception as e:
                pass  # لا نوقف العملية إذا فشل التحليل
        
        return instance
    
    @action(detail=True, methods=['post'])
    def analyze(self, request, pk=None):
        """تحليل الملف الصوتي"""
        try:
            instance = self.get_object()
            processor = AudioProcessor()
            file_path = instance.audio_file.path
            audio_data, sr = processor.load_audio(file_path)
            analysis = processor.analyze_audio(audio_data)
            
            return Response({
                'status': 'success',
                'analysis': {
                    'bpm': analysis['bpm'],
                    'key': analysis['key'],
                    'duration': analysis['duration'],
                    'spectral_centroid': float(analysis['spectral_centroid']),
                    'spectral_rolloff': float(analysis['spectral_rolloff']),
                    'spectral_bandwidth': float(analysis['spectral_bandwidth']),
                }
            })
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class RemixProjectViewSet(viewsets.ModelViewSet):
    """ViewSet لإدارة مشاريع الريمكس"""
    queryset = RemixProject.objects.all()
    serializer_class = RemixProjectSerializer
    
    def perform_create(self, serializer):
        return serializer.save()
    
    @action(detail=True, methods=['post'])
    def add_source(self, request, pk=None):
        """إضافة مصدر صوتي للمشروع"""
        try:
            project = self.get_object()
            audio_source_id = request.data.get('audio_source_id')
            volume = float(request.data.get('volume', 1.0))
            start_time = float(request.data.get('start_time', 0.0))
            end_time = request.data.get('end_time')
            is_loop = request.data.get('is_loop', False)
            fade_in = float(request.data.get('fade_in', 0.0))
            fade_out = float(request.data.get('fade_out', 0.0))
            order = int(request.data.get('order', 0))
            
            audio_source = AudioSource.objects.get(id=audio_source_id)
            
            remix_source = RemixSource.objects.create(
                project=project,
                audio_source=audio_source,
                volume=volume,
                start_time=start_time,
                end_time=float(end_time) if end_time else None,
                is_loop=is_loop,
                fade_in=fade_in,
                fade_out=fade_out,
                order=order
            )
            
            serializer = RemixSourceSerializer(remix_source)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except AudioSource.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Audio source not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def remove_source(self, request, pk=None):
        """إزالة مصدر صوتي من المشروع"""
        try:
            project = self.get_object()
            audio_source_id = request.data.get('audio_source_id')
            
            remix_source = RemixSource.objects.get(
                project=project,
                audio_source_id=audio_source_id
            )
            remix_source.delete()
            
            return Response({
                'status': 'success',
                'message': 'Source removed successfully'
            })
        except RemixSource.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Remix source not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'])
    def generate_remix(self, request, pk=None):
        """توليد الريمكس"""
        try:
            project = self.get_object()
            
            # تحديث حالة المشروع
            project.status = RemixProject.Status.PROCESSING
            project.save()
            
            # الحصول على المصادر
            remix_sources = project.sources.all().order_by('order')
            if not remix_sources.exists():
                return Response({
                    'status': 'error',
                    'message': 'No audio sources in project'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # إعداد البيانات
            serializer = RemixRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            config = serializer.validated_data
            
            # إنشاء مولد الريمكس
            generator = AIRemixGenerator()
            
            # تجهيز المصادر
            sources_data = []
            for remix_source in remix_sources:
                source_data = {
                    'file_path': remix_source.audio_source.audio_file.path,
                    'volume': remix_source.volume,
                    'fade_in': remix_source.fade_in,
                    'fade_out': remix_source.fade_out,
                    'is_loop': remix_source.is_loop,
                    'start_time': remix_source.start_time,
                    'end_time': remix_source.end_time
                }
                sources_data.append(source_data)
            
            # الترتيب التلقائي إذا طلب المستخدم
            if config.get('auto_arrange'):
                # حساب المدة الكلية
                total_duration = sum(
                    (s.get('end_time', 0) - s.get('start_time', 0)) 
                    for s in sources_data 
                    if s.get('end_time')
                )
                if total_duration == 0:
                    total_duration = 180  # 3 دقائق افتراضياً
                sources_data = generator.auto_arrange(sources_data, total_duration)
            
            # الخلط الذكي إذا طلب المستخدم
            if config.get('intelligent_mix'):
                sources_data = generator.intelligent_mix(sources_data)
            
            # إعداد التكوين المستهدف
            target_config = {
                'target_bpm': config.get('target_bpm') or project.target_bpm,
                'target_key': config.get('target_key') or project.target_key,
                'effects': config.get('effects', {})
            }
            
            # توليد الريمكس
            remix_audio = generator.generate_remix(sources_data, target_config)
            
            # حفظ الملف
            output_filename = f"remix_{uuid.uuid4().hex}.wav"
            output_path = os.path.join(settings.MEDIA_ROOT, 'ai_remix', 'outputs', output_filename)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            generator.processor.save_audio(remix_audio, output_path, format='wav')
            
            # إنشاء سجل المخرجات
            output = RemixOutput.objects.create(
                project=project,
                output_file=f'ai_remix/outputs/{output_filename}',
                format='wav',
                duration=len(remix_audio) / generator.processor.sample_rate,
                file_size=os.path.getsize(output_path)
            )
            
            # تحديث حالة المشروع
            project.status = RemixProject.Status.COMPLETED
            project.save()
            
            serializer = RemixOutputSerializer(output)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            project.status = RemixProject.Status.FAILED
            project.save()
            
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def neural_generate(self, request, pk=None):
        """توليد الريمكس باستخدام الشبكة العصبية (غير متاح بدون PyTorch)"""
        return Response({
            'status': 'error',
            'message': 'Neural remix requires PyTorch. Please install PyTorch or use the standard remix method.'
        }, status=status.HTTP_501_NOT_IMPLEMENTED)


class RemixSourceViewSet(viewsets.ModelViewSet):
    """ViewSet لإدارة مصادر الريمكس"""
    queryset = RemixSource.objects.all()
    serializer_class = RemixSourceSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        project_id = self.request.query_params.get('project_id')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        return queryset


class RemixOutputViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet لعرض مخرجات الريمكس"""
    queryset = RemixOutput.objects.all()
    serializer_class = RemixOutputSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        project_id = self.request.query_params.get('project_id')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        return queryset


class AIModelViewSet(viewsets.ModelViewSet):
    """ViewSet لإدارة نماذج الذكاء الاصطناعي"""
    queryset = AIModel.objects.all()
    serializer_class = AIModelSerializer
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """تفعيل النموذج"""
        try:
            model = self.get_object()
            
            # تعطيل جميع النماذج الأخرى
            AIModel.objects.update(is_active=False)
            
            # تفعيل النموذج المحدد
            model.is_active = True
            model.save()
            
            return Response({
                'status': 'success',
                'message': f'Model {model.name} activated successfully'
            })
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def quick_remix(request, **kwargs):
    """إنشاء ريمكس سريع من أغنيتين"""
    try:
        song1_id = request.data.get('song1_id')
        song2_id = request.data.get('song2_id')
        
        if not song1_id or not song2_id:
            return Response({
                'status': 'error',
                'message': 'Both song IDs are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # الحصول على الأغاني
        try:
            song1 = Song.objects.get(id=song1_id)
            song2 = Song.objects.get(id=song2_id)
        except Song.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'One or both songs not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # التأكد من وجود ملفات صوتية
        if not song1.audio_file or not song2.audio_file:
            return Response({
                'status': 'error',
                'message': 'One or both songs do not have audio files'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # إنشاء مشروع الريمكس
        project_name = f"Remix: {song1.title_ar or song1.title_en} + {song2.title_ar or song2.title_en}"
        project = RemixProject.objects.create(
            name=project_name,
            status=RemixProject.Status.PROCESSING
        )
        
        # إنشاء مصادر صوتية من الأغاني
        source1 = AudioSource.objects.create(
            name=f"{song1.title_ar or song1.title_en} (Audio)",
            audio_file=song1.audio_file,
            source_type=AudioSource.SourceType.OTHER
        )
        
        source2 = AudioSource.objects.create(
            name=f"{song2.title_ar or song2.title_en} (Audio)",
            audio_file=song2.audio_file,
            source_type=AudioSource.SourceType.OTHER
        )
        
        # إضافة المصادر للمشروع
        RemixSource.objects.create(
            project=project,
            audio_source=source1,
            volume=1.0,
            order=0
        )
        
        RemixSource.objects.create(
            project=project,
            audio_source=source2,
            volume=1.0,
            order=1

        )
        
        # توليد الريمكس
        generator = AIRemixGenerator()
        
        sources_data = [
            {
                'file_path': source1.audio_file.path,
                'volume': 1.0,
                'fade_in': 0.0,
                'fade_out': 0.0
            },
            {
                'file_path': source2.audio_file.path,
                'volume': 1.0,
                'fade_in': 0.0,
                'fade_out': 0.0
            }
        ]
        
        target_config = {
            'target_bpm': None,
            'target_key': None,
            'effects': {
                'compressor': True,
                'limiter': True
            }
        }
        
        remix_audio = generator.generate_remix(sources_data, target_config)
        
        # حفظ الملف
        output_filename = f"quick_remix_{uuid.uuid4().hex}.wav"
        output_path = os.path.join(settings.MEDIA_ROOT, 'ai_remix', 'outputs', output_filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        generator.processor.save_audio(remix_audio, output_path, format='wav')
        
        # إنشاء سجل المخرجات
        output = RemixOutput.objects.create(
            project=project,
            output_file=f'ai_remix/outputs/{output_filename}',
            format='wav',
            duration=len(remix_audio) / generator.processor.sample_rate,
            file_size=os.path.getsize(output_path)
        )
        
        # تحديث حالة المشروع
        project.status = RemixProject.Status.COMPLETED
        project.save()
        
        return Response({
            'status': 'success',
            'remix_id': project.id,
            'output_id': output.id,
            'message': 'Remix created successfully'
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
