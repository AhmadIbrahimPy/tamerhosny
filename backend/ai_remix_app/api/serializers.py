from rest_framework import serializers
from backend.ai_remix_app.models import AudioSource, RemixProject, RemixSource, RemixOutput, AIModel


class AudioSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AudioSource
        fields = ['id', 'name', 'audio_file', 'source_type', 'bpm', 'key', 'duration', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']


class RemixSourceSerializer(serializers.ModelSerializer):
    audio_source_details = AudioSourceSerializer(source='audio_source', read_only=True)
    
    class Meta:
        model = RemixSource
        fields = ['id', 'audio_source', 'audio_source_details', 'volume', 'start_time', 'end_time', 
                  'is_loop', 'fade_in', 'fade_out', 'order']
        read_only_fields = ['id']


class RemixProjectSerializer(serializers.ModelSerializer):
    sources = RemixSourceSerializer(many=True, read_only=True)
    outputs = serializers.SerializerMethodField()
    
    class Meta:
        model = RemixProject
        fields = ['id', 'name', 'description', 'status', 'target_bpm', 'target_key', 
                  'created_at', 'updated_at', 'sources', 'outputs']
        read_only_fields = ['id', 'created_at', 'updated_at', 'status']
    
    def get_outputs(self, obj):
        outputs = obj.outputs.all()
        return RemixOutputSerializer(outputs, many=True).data


class RemixOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = RemixOutput
        fields = ['id', 'project', 'output_file', 'format', 'bitrate', 'sample_rate', 
                  'duration', 'file_size', 'created_at']
        read_only_fields = ['id', 'created_at', 'duration', 'file_size']


class AIModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIModel
        fields = ['id', 'name', 'version', 'model_type', 'description', 'is_active', 
                  'model_path', 'created_at']
        read_only_fields = ['id', 'created_at']


class RemixRequestSerializer(serializers.Serializer):
    """Serializer لطلب إنشاء ريمكس"""
    project_id = serializers.IntegerField()
    target_bpm = serializers.IntegerField(required=False, allow_null=True)
    target_key = serializers.CharField(max_length=10, required=False, allow_blank=True)
    effects = serializers.DictField(required=False, allow_null=True)
    auto_arrange = serializers.BooleanField(default=False)
    intelligent_mix = serializers.BooleanField(default=False)
