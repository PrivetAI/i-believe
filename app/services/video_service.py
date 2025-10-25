"""
Video service - MAXIMUM OPTIMIZATION with GPU encoding
"""
import sys
import gc
import subprocess
from pathlib import Path
from typing import List, Tuple
from moviepy.editor import (
    ImageClip, AudioFileClip, CompositeVideoClip,
    concatenate_videoclips, ColorClip, VideoClip
)

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from models.slide import Slide
from utils.ken_burns import apply_ken_burns_optimized
from utils.subtitle_renderer import render_subtitles
from utils.transitions import apply_transitions
from utils.logger import get_logger

logger = get_logger(__name__)


def check_gpu_available() -> bool:
    """Check if Intel GPU encoding is available - try multiple methods"""
    if not config.GPU_ENCODING_ENABLED:
        return False
    
    # Try QSV first
    try:
        logger.info("Testing h264_qsv encoder...")
        test_result = subprocess.run(
            [
                'ffmpeg', '-f', 'lavfi', '-i', 'color=black:s=64x64:d=0.1',
                '-c:v', 'h264_qsv', '-global_quality', '26',
                '-f', 'null', '-'
            ],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if test_result.returncode == 0:
            logger.info("✓ QSV encoder test successful")
            return True
        else:
            logger.info(f"QSV test failed, trying VAAPI...")
    except:
        pass
    
    # Try VAAPI as fallback
    try:
        logger.info("Testing h264_vaapi encoder...")
        test_result = subprocess.run(
            [
                'ffmpeg', '-vaapi_device', '/dev/dri/renderD128',
                '-f', 'lavfi', '-i', 'color=black:s=64x64:d=0.1',
                '-vf', 'format=nv12,hwupload',
                '-c:v', 'h264_vaapi', '-qp', '26',
                '-f', 'null', '-'
            ],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if test_result.returncode == 0:
            logger.info("✓ VAAPI encoder test successful")
            return True
        else:
            logger.warning(f"VAAPI test failed: {test_result.stderr}")
    except Exception as e:
        logger.warning(f"VAAPI check failed: {e}")
    
    return False


class VideoService:
    """Service for video generation - MAXIMUM OPTIMIZATION"""
    
    def __init__(self, resolution: Tuple[int, int]):
        """
        Initialize video service with Intel GPU detection (QSV or VAAPI)
        
        Args:
            resolution: Video resolution (width, height)
        """
        self.resolution = resolution
        self.gpu_available = check_gpu_available()
        self.use_vaapi = False
        
        # Determine encoder type
        if self.gpu_available:
            # Check which encoder worked
            try:
                test = subprocess.run(
                    ['ffmpeg', '-f', 'lavfi', '-i', 'color=black:s=64x64:d=0.1',
                     '-c:v', 'h264_qsv', '-f', 'null', '-'],
                    capture_output=True, timeout=5
                )
                self.use_vaapi = (test.returncode != 0)
            except:
                self.use_vaapi = True
            
            encoder_name = "VAAPI" if self.use_vaapi else "QSV"
            logger.info(f"🚀 Intel {encoder_name} GPU encoding ENABLED")
        else:
            logger.info("💻 Using CPU encoding (libx264)")
        
        logger.info(f"VideoService initialized: {resolution[0]}x{resolution[1]} @ {config.DEFAULT_FPS}fps")
    
    def create_slide_clip(
        self,
        image_path: str,
        audio_path: str,
        duration: float
    ) -> VideoClip:
        """
        Create optimized video clip with minimal memory usage
        """
        logger.info(f"Creating slide clip: {Path(image_path).name}")
        
        try:
            # Load image
            img_clip = ImageClip(image_path)
            
            # Resize to fit (maintain aspect ratio)
            img_clip = img_clip.resize(height=self.resolution[1])
            if img_clip.w < self.resolution[0]:
                img_clip = img_clip.resize(width=self.resolution[0])
            
            img_clip = img_clip.set_duration(duration)
            
            # Apply OPTIMIZED Ken Burns
            kb_params = {
                'direction': 'zoom_in',
                'zoom_start': 1.0,
                'zoom_end': 1.2,
                'pan_x': 0.1,
                'pan_y': 0.1
            }
            img_clip = apply_ken_burns_optimized(img_clip, kb_params, duration)
            
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
            
            logger.info("Slide clip created")
            return video_clip
            
        except Exception as e:
            logger.error(f"Failed to create slide clip: {e}")
            raise
    
    def get_ffmpeg_params(self) -> Tuple[str, dict]:
        """
        Get optimal FFmpeg parameters (QSV, VAAPI, or CPU)
        
        Returns:
            (codec, ffmpeg_params_dict)
        """
        if self.gpu_available:
            if self.use_vaapi:
                # Intel VAAPI encoding
                codec = 'h264_vaapi'
                params = [
                    '-vaapi_device', '/dev/dri/renderD128',
                    '-vf', 'format=nv12,hwupload',
                    '-qp', '26',
                    '-pix_fmt', 'vaapi_vld',
                    '-movflags', '+faststart'
                ]
                logger.info("Using Intel VAAPI GPU encoding")
            else:
                # Intel QSV encoding
                codec = 'h264_qsv'
                params = [
                    '-global_quality', '26',
                    '-preset', 'veryfast',
                    '-pix_fmt', 'nv12',
                    '-movflags', '+faststart'
                ]
                logger.info("Using Intel QSV GPU encoding")
        else:
            # CPU encoding fallback
            codec = 'libx264'
            params = [
                '-crf', str(config.CRF),
                '-preset', config.MOVIEPY_PRESET,
                '-pix_fmt', 'yuv420p',
                '-movflags', '+faststart',
                '-tune', 'fastdecode',
                '-x264-params', 'ref=2:bframes=1:me=hex:subme=2:trellis=0'
            ]
            logger.info("Using CPU encoding (libx264)")
        
        return codec, params
    
    def assemble_video(
        self,
        slides: List[Slide],
        output_path: str,
        words_per_slide: List[List[dict]] = None
    ) -> str:
        """
        Assemble final video - MAXIMUM OPTIMIZATION
        
        Key optimizations:
        - GPU encoding when available
        - Aggressive garbage collection
        - Optimized FFmpeg params
        - Memory-efficient processing
        """
        logger.info(f"Assembling video: {len(slides)} slides")
        
        slide_clips = []
        
        try:
            # Process slides with memory management
            for i, slide in enumerate(slides):
                logger.info(f"Processing slide {i+1}/{len(slides)}")
                
                duration = max(slide.duration, config.MIN_SLIDE_DURATION)
                clip = self.create_slide_clip(slide.image_path, slide.audio_path, duration)
                
                # Add subtitles (optimized with global cache)
                if words_per_slide and i < len(words_per_slide) and words_per_slide[i]:
                    logger.info(f"Adding {len(words_per_slide[i])} word subtitles")
                    clip = render_subtitles(clip, words_per_slide[i], self.resolution)
                
                slide_clips.append(clip)
                
                # Aggressive GC every N slides
                if config.GC_COLLECT_AFTER_SLIDE and (i + 1) % config.GC_COLLECT_INTERVAL == 0:
                    gc.collect()
                    logger.debug(f"GC collected at slide {i+1}")
            
            logger.info("Applying transitions")
            final_clip = apply_transitions(slide_clips)
            
            # Get optimal encoding params
            codec, ffmpeg_params = self.get_ffmpeg_params()
            
            logger.info(f"Rendering video: {output_path}")
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Try rendering with selected codec, fallback to CPU if fails
            try:
                final_clip.write_videofile(
                    output_path,
                    fps=config.DEFAULT_FPS,
                    codec=codec,
                    audio_codec=config.DEFAULT_AUDIO_CODEC,
                    threads=config.MOVIEPY_THREADS,
                    logger=None,
                    verbose=False,
                    ffmpeg_params=ffmpeg_params
                )
            except Exception as e:
                if self.gpu_available and 'h264_qsv' in str(e):
                    logger.warning(f"GPU encoding failed, falling back to CPU: {e}")
                    self.gpu_available = False
                    codec, ffmpeg_params = self.get_ffmpeg_params()
                    
                    # Retry with CPU
                    final_clip.write_videofile(
                        output_path,
                        fps=config.DEFAULT_FPS,
                        codec=codec,
                        audio_codec=config.DEFAULT_AUDIO_CODEC,
                        threads=config.MOVIEPY_THREADS,
                        logger=None,
                        verbose=False,
                        ffmpeg_params=ffmpeg_params
                    )
                else:
                    raise
            
            logger.info("✓ Video rendered successfully")
            
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