"""
Video Generation Pipeline - isolated business logic
"""
import uuid
import time
import shutil
import requests
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Callable

from core.models.slide import Slide
from core.services.tts_service import TTSService
from core.services.whisper_service import WhisperService
from core.services.video_service import VideoService
from utils.logger import get_logger
import config

logger = get_logger(__name__)


class VideoPipeline:
    """Isolated video generation pipeline"""
    
    def __init__(self, generation_id: str = None):
        self.generation_id = generation_id or str(uuid.uuid4())
        self.cache_dir = Path("cache") / self.generation_id
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Pipeline initialized: {self.generation_id}")
    
    def download_image(self, url: str, filename: str) -> str:
        """Download image from URL to cache"""
        images_dir = self.cache_dir / "images"
        images_dir.mkdir(exist_ok=True)
        
        file_path = images_dir / filename
        
        logger.info(f"Downloading image: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        with open(file_path, 'wb') as f:
            f.write(response.content)
        
        logger.info(f"Image downloaded: {filename}")
        return str(file_path)
    
    def prepare_slides(
        self, 
        slides_data: List[Dict],
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> List[Dict]:
        """
        Prepare slides: download external images if needed
        
        Args:
            slides_data: List of {text, image_path?, image_url?}
            progress_callback: Optional callback(progress, message)
        
        Returns:
            List of {text, image_path}
        """
        prepared = []
        
        for i, slide_data in enumerate(slides_data):
            if progress_callback:
                progress_callback(i / len(slides_data) * 0.1, f"Preparing slide {i+1}/{len(slides_data)}")
            
            # Handle external URL
            if 'image_url' in slide_data and slide_data['image_url']:
                filename = f"slide_{i}_{uuid.uuid4().hex[:8]}.jpg"
                image_path = self.download_image(slide_data['image_url'], filename)
            # Handle local path
            elif 'image_path' in slide_data and slide_data['image_path']:
                image_path = slide_data['image_path']
            else:
                raise ValueError(f"Slide {i}: no image_path or image_url provided")
            
            prepared.append({
                'text': slide_data['text'],
                'image_path': image_path
            })
        
        return prepared
    
    def generate_audio(
        self,
        slides_data: List[Dict],
        voice: str,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> List[Slide]:
        """
        Generate TTS audio for all slides
        
        Args:
            slides_data: List of {text, image_path}
            voice: Edge TTS voice
            progress_callback: Optional callback(progress, message)
        
        Returns:
            List of Slide objects with audio
        """
        audio_dir = self.cache_dir / "audio"
        audio_dir.mkdir(exist_ok=True)
        
        tts_service = TTSService()
        slide_objects = []
        
        for i, slide_data in enumerate(slides_data):
            if progress_callback:
                progress = 0.1 + (i / len(slides_data)) * 0.25
                progress_callback(progress, f"Generating audio {i+1}/{len(slides_data)}")
            
            logger.info(f"Generating TTS for slide {i+1}/{len(slides_data)}")
            
            audio_path = audio_dir / f"slide_{i}.mp3"
            duration = tts_service.generate_audio(
                slide_data['text'],
                voice,
                str(audio_path)
            )
            
            slide_obj = Slide(
                text=slide_data['text'],
                image_path=slide_data['image_path'],
                audio_path=str(audio_path),
                duration=duration
            )
            slide_objects.append(slide_obj)
        
        return slide_objects
    
    def generate_timestamps(
        self,
        slides: List[Slide],
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> List[List[Dict]]:
        """
        Generate word-level timestamps with Whisper
        
        Args:
            slides: List of Slide objects
            progress_callback: Optional callback(progress, message)
        
        Returns:
            List of word lists per slide
        """
        whisper_service = WhisperService()
        words_per_slide = []
        
        for i, slide in enumerate(slides):
            if progress_callback:
                progress = 0.35 + (i / len(slides)) * 0.25
                progress_callback(progress, f"Transcribing {i+1}/{len(slides)}")
            
            logger.info(f"Transcribing slide {i+1}/{len(slides)}")
            
            words = whisper_service.transcribe_with_timestamps(slide.audio_path)
            words_per_slide.append(words)
        
        return words_per_slide
    
    def assemble_video(
        self,
        slides: List[Slide],
        words_per_slide: List[List[Dict]],
        resolution: Tuple[int, int],
        output_path: str,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> str:
        """
        Assemble final video
        
        Args:
            slides: List of Slide objects
            words_per_slide: Word timestamps per slide
            resolution: (width, height)
            output_path: Output video path
            progress_callback: Optional callback(progress, message)
        
        Returns:
            Path to generated video
        """
        if progress_callback:
            progress_callback(0.6, "Assembling video...")
        
        video_service = VideoService(resolution)
        video_path = video_service.assemble_video(
            slides,
            output_path,
            words_per_slide
        )
        
        if progress_callback:
            progress_callback(1.0, "Video completed!")
        
        return video_path
    
    def cleanup(self):
        """Clean up cache directory"""
        if config.CACHE_AUTO_CLEANUP:
            if self.cache_dir.exists():
                try:
                    shutil.rmtree(self.cache_dir)
                    logger.info(f"Cache cleaned up: {self.generation_id}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup cache: {e}")
    
    def generate(
        self,
        slides_data: List[Dict],
        voice: str,
        resolution: Tuple[int, int],
        output_path: str,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> Dict:
        """
        Full video generation pipeline
        
        Args:
            slides_data: List of {text, image_path?, image_url?}
            voice: Edge TTS voice
            resolution: (width, height)
            output_path: Output video path
            progress_callback: Optional callback(progress, message)
        
        Returns:
            Dict with video_path, duration, file_size_mb
        """
        start_time = time.time()
        
        try:
            logger.info("="*50)
            logger.info("Starting video generation")
            logger.info(f"Generation ID: {self.generation_id}")
            logger.info(f"Slides: {len(slides_data)}")
            logger.info(f"Voice: {voice}")
            logger.info(f"Resolution: {resolution[0]}x{resolution[1]}")
            logger.info("="*50)
            
            # Step 1: Prepare slides (download images if needed)
            slides_data = self.prepare_slides(slides_data, progress_callback)
            
            # Step 2: Generate audio
            slides = self.generate_audio(slides_data, voice, progress_callback)
            
            # Step 3: Generate timestamps
            words_per_slide = self.generate_timestamps(slides, progress_callback)
            
            # Step 4: Assemble video
            video_path = self.assemble_video(
                slides, 
                words_per_slide, 
                resolution, 
                output_path,
                progress_callback
            )
            
            # Calculate stats
            total_duration = sum(s.duration for s in slides)
            file_size_mb = Path(video_path).stat().st_size / (1024 * 1024)
            generation_time = time.time() - start_time
            
            logger.info("="*50)
            logger.info("Video generation completed!")
            logger.info(f"Output: {video_path}")
            logger.info(f"Duration: {total_duration:.2f}s")
            logger.info(f"File size: {file_size_mb:.2f}MB")
            logger.info(f"Generation time: {generation_time:.2f}s")
            logger.info("="*50)
            
            # Cleanup
            self.cleanup()
            
            return {
                'video_path': video_path,
                'duration': total_duration,
                'file_size_mb': file_size_mb,
                'generation_time': generation_time
            }
            
        except Exception as e:
            logger.error(f"Video generation failed: {e}", exc_info=True)
            raise