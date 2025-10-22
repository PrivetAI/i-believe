"""
Video service for assembling final video from slides
"""
import sys
from pathlib import Path
from typing import List, Tuple
from moviepy.editor import (
    ImageClip, AudioFileClip, CompositeVideoClip,
    concatenate_videoclips, ColorClip, VideoClip
)

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from models.slide import Slide
from utils.ken_burns import generate_ken_burns_params, apply_ken_burns
from utils.subtitle_renderer import render_subtitles
from utils.transitions import apply_transitions
from utils.logger import get_logger

logger = get_logger(__name__)


class VideoService:
    """Service for video generation and assembly"""
    
    def __init__(self, resolution: Tuple[int, int]):
        """
        Initialize video service
        
        Args:
            resolution: Video resolution (width, height)
        """
        self.resolution = resolution
        logger.info(f"VideoService initialized with resolution: {resolution[0]}x{resolution[1]}")
    
    def create_slide_clip(
        self,
        image_path: str,
        audio_path: str,
        duration: float
    ) -> VideoClip:
        """
        Create a video clip from image and audio with Ken Burns effect
        
        Args:
            image_path: Path to image file
            audio_path: Path to audio file
            duration: Clip duration in seconds
            
        Returns:
            VideoClip with image, audio, and Ken Burns effect
        """
        logger.info(f"Creating slide clip: {Path(image_path).name}")
        logger.debug(f"Duration: {duration}s")
        
        try:
            # Load image
            img_clip = ImageClip(image_path)
            
            # Resize to fit resolution while maintaining aspect ratio
            img_clip = img_clip.resize(height=self.resolution[1])
            if img_clip.w < self.resolution[0]:
                img_clip = img_clip.resize(width=self.resolution[0])
            
            # Set duration
            img_clip = img_clip.set_duration(duration)
            
            # Apply Ken Burns effect
            kb_params = generate_ken_burns_params()
            img_clip = apply_ken_burns(img_clip, kb_params, duration)
            
            # Create background (black bars if needed)
            bg_clip = ColorClip(
                size=self.resolution,
                color=(0, 0, 0),
                duration=duration
            )
            
            # Composite image on background
            video_clip = CompositeVideoClip(
                [bg_clip, img_clip.set_position('center')],
                size=self.resolution
            )
            
            # Add audio
            if audio_path and Path(audio_path).exists():
                audio = AudioFileClip(audio_path)
                video_clip = video_clip.set_audio(audio)
                logger.debug("Audio attached to clip")
            
            logger.info("Slide clip created successfully")
            return video_clip
            
        except Exception as e:
            logger.error(f"Failed to create slide clip: {e}")
            raise
    
    def assemble_video(
        self,
        slides: List[Slide],
        output_path: str,
        words_per_slide: List[List[dict]] = None
    ) -> str:
        """
        Assemble final video from slides with subtitles
        Optimized: parallel processing where possible, minimize I/O
        """
        logger.info(f"Assembling video with {len(slides)} slides")
        
        try:
            slide_clips = []
            
            for i, slide in enumerate(slides):
                logger.info(f"Processing slide {i+1}/{len(slides)}")
                
                duration = max(slide.duration, config.MIN_SLIDE_DURATION)
                clip = self.create_slide_clip(slide.image_path, slide.audio_path, duration)
                
                # Add subtitles if available
                if words_per_slide and i < len(words_per_slide) and words_per_slide[i]:
                    logger.info(f"Adding {len(words_per_slide[i])} word subtitles")
                    clip = render_subtitles(clip, words_per_slide[i], self.resolution)
                
                slide_clips.append(clip)
            
            logger.info("Applying transitions")
            final_clip = apply_transitions(slide_clips)
            
            logger.info(f"Rendering final video: {output_path}")
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            final_clip.write_videofile(
                output_path,
                fps=config.DEFAULT_FPS,
                codec=config.DEFAULT_CODEC,
                audio_codec=config.DEFAULT_AUDIO_CODEC,
                preset='ultrafast',
                threads=6,
                logger=None
            )
            
            logger.info("Video assembly completed")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to assemble video: {e}")
            raise
        finally:
            for clip in slide_clips:
                try:
                    clip.close()
                except:
                    pass