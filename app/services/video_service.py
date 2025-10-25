"""
Video service - Aggressive optimization for rendering speed
"""
import sys
import gc
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
    """Service for video generation - Maximum speed optimization"""
    
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
        Create optimized video clip from image and audio
        """
        logger.info(f"Creating slide clip: {Path(image_path).name}")
        
        try:
            # Load image
            img_clip = ImageClip(image_path)
            
            # Resize to fit resolution (maintain aspect ratio)
            img_clip = img_clip.resize(height=self.resolution[1])
            if img_clip.w < self.resolution[0]:
                img_clip = img_clip.resize(width=self.resolution[0])
            
            img_clip = img_clip.set_duration(duration)
            
            # Apply Ken Burns effect
            kb_params = generate_ken_burns_params()
            img_clip = apply_ken_burns(img_clip, kb_params, duration)
            
            # Create background
            bg_clip = ColorClip(
                size=self.resolution,
                color=(0, 0, 0),
                duration=duration
            )
            
            # Composite
            video_clip = CompositeVideoClip(
                [bg_clip, img_clip.set_position('center')],
                size=self.resolution
            )
            
            # Add audio
            if audio_path and Path(audio_path).exists():
                audio = AudioFileClip(audio_path)
                video_clip = video_clip.set_audio(audio)
            
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
        Assemble final video - MAXIMUM speed optimization
        """
        logger.info(f"Assembling video with {len(slides)} slides")
        
        try:
            slide_clips = []
            
            # Process slides
            for i, slide in enumerate(slides):
                logger.info(f"Processing slide {i+1}/{len(slides)}")
                
                duration = max(slide.duration, config.MIN_SLIDE_DURATION)
                clip = self.create_slide_clip(slide.image_path, slide.audio_path, duration)
                
                # Add subtitles if available
                if words_per_slide and i < len(words_per_slide) and words_per_slide[i]:
                    logger.info(f"Adding {len(words_per_slide[i])} word subtitles")
                    clip = render_subtitles(clip, words_per_slide[i], self.resolution)
                
                slide_clips.append(clip)
                
                # Force garbage collection
                if config.GC_COLLECT_AFTER_SLIDE:
                    gc.collect()
            
            logger.info("Applying transitions")
            final_clip = apply_transitions(slide_clips)
            
            logger.info(f"Starting final render: {output_path}")
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # AGGRESSIVE render settings for maximum speed
            final_clip.write_videofile(
                output_path,
                fps=config.DEFAULT_FPS,
                codec=config.DEFAULT_CODEC,
                audio_codec=config.DEFAULT_AUDIO_CODEC,
                preset='ultrafast',  # Changed to ultrafast for maximum speed
                threads=config.MOVIEPY_THREADS,
                logger=None,
                verbose=False,
                ffmpeg_params=[
                    '-crf', str(config.CRF),
                    '-pix_fmt', 'yuv420p',
                    '-movflags', '+faststart',
                    '-tune', 'fastdecode',  # Optimize for fast decoding
                    '-x264-params', 'ref=1:bframes=0:me=dia:subme=1:trellis=0',  # Speed optimizations
                ]
            )
            
            logger.info("Video rendered successfully")
            
            # Cleanup
            final_clip.close()
            for clip in slide_clips:
                try:
                    clip.close()
                except:
                    pass
            
            gc.collect()
            
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to assemble video: {e}")
            raise
        finally:
            # Emergency cleanup
            try:
                for clip in slide_clips:
                    clip.close()
            except:
                pass
            gc.collect()