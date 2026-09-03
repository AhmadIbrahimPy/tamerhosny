"""
Vocal Remover - Uses StemSeparator from ai_remix_app for AI-based vocal separation
Uses the same Demucs implementation that works in the Remix feature
"""

import os
import subprocess
from pathlib import Path
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class VocalRemover:
    """
    Uses StemSeparator from ai_remix_app for AI-based vocal separation
    This provides real AI vocal isolation using Demucs
    """
    
    def __init__(self):
        self.output_dir = str(os.path.join(settings.MEDIA_ROOT, 'instrumental_versions'))
        os.makedirs(self.output_dir, exist_ok=True)
    
    def remove_vocals(self, audio_path: str) -> str:
        """
        Remove vocals using StemSeparator from ai_remix_app
        
        Args:
            audio_path: Path to the original audio file
            
        Returns:
            Path to the newly created instrumental file
        """
        try:
            # Convert to string if it's a Path object
            audio_path = str(audio_path)
            
            logger.info(f"Starting vocal separation...")
            logger.info(f"Input: {audio_path}")
            
            audio_filename = Path(audio_path).stem
            final_filename = f"{str(audio_filename)}_instrumental.mp3"
            final_path = os.path.join(self.output_dir, final_filename)
            
            # Use StemSeparator from ai_remix_app
            from backend.ai_remix_app.core.stem_separator import StemSeparator
            
            # Create StemSeparator instance
            separator = StemSeparator(output_dir=self.output_dir)
            
            # Get instrumental using Demucs
            instrumental_wav = separator.get_instrumental(audio_path)
            
            # Convert to MP3
            self._convert_to_mp3(instrumental_wav, final_path)
            
            # Verify the output file exists and has content
            if not os.path.exists(final_path):
                raise FileNotFoundError(f"Output file not created at {final_path}")
            
            file_size = os.path.getsize(final_path)
            if file_size == 0:
                raise RuntimeError(f"Output file is empty: {final_path}")
            
            logger.info(f"AI vocal separation completed")
            logger.info(f"Output: {final_path} (size: {file_size} bytes)")
            
            return final_path.replace(str(settings.MEDIA_ROOT) + '/', '')
                
        except Exception as e:
            logger.error(f"Vocal removal failed: {str(e)}")
            raise RuntimeError(f"Vocal removal failed: {str(e)}")
    
    def _convert_to_mp3(self, input_path: str, output_path: str):
        """
        Convert WAV to high-quality MP3
        """
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-codec:a', 'libmp3lame',
            '-b:a', '320k',
            '-y',
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"MP3 conversion failed: {result.stderr}")
