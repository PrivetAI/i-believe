"""
Video service - MoviePy-compatible GPU encoding
"""
import subprocess
from pathlib import Path
import sys
import gc
import os
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


def detect_best_encoder() -> tuple[bool, bool]:
    """
    Detect available Intel GPU encoder
    
    Returns:
        (gpu_available: bool, use_vaapi: bool)
    """
    if not config.GPU_ENCODING_ENABLED:
        logger.info("GPU encoding disabled in config")
        return False, False
    
    # Test VAAPI (Intel iGPU)
    logger.info("Testing h264_vaapi encoder...")
    try:
        result = subprocess.run(
            [
                'ffmpeg', '-init_hw_device', 'vaapi=va:/dev/dri/renderD128',
                '-hwaccel', 'vaapi', '-hwaccel_output_format', 'vaapi',
                '-hwaccel_device', 'va',
                '-f', 'lavfi', '-i', 'color=black:s=64x64:d=0.1',
                '-vf', 'format=nv12,hwupload',
                '-c:v', 'h264_vaapi', '-qp', '26',
                '-f', 'null', '-'
            ],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            logger.info("✓ VAAPI encoder available")
            return True, True
        else:
            logger.debug(f"VAAPI test stderr: {result.stderr[:200]}")
    except Exception as e:
        logger.debug(f"VAAPI test failed: {e}")
    
    # Test QSV as fallback
    logger.info("Testing h264_qsv encoder...")
    try:
        result = subprocess.run(
            [
                'ffmpeg', '-f', 'lavfi', '-i', 'color=black:s=64x64:d=0.1',
                '-c:v', 'h264_qsv', '-global_quality', '26',
                '-f', 'null', '-'
            ],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            logger.info("✓ QSV encoder available")
            return True, False
    except Exception as e:
        logger.debug(f"QSV test failed: {e}")
    
    logger.info("No GPU encoder available, using CPU")
    return False, False


class VideoService:
    """Service for video generation with GPU acceleration"""
    
    def __init__(self, resolution: Tuple[int, int]):
        """
        Initialize video service with GPU detection
        
        Args:
            resolution: Video resolution (width, height)
        """
        self.resolution = resolution
        
        # Detect GPU encoder
        self.gpu_available, self.use_vaapi = detect_best_encoder()
        
        if self.gpu_available:
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
        """Create optimized video clip with minimal memory usage"""
        logger.info(f"Creating slide clip: {Path(image_path).name}")
        
        try:
            # Load image
            img_clip = ImageClip(image_path)
            
            # Resize to fit
            img_clip = img_clip.resize(height=self.resolution[1])
            if img_clip.w < self.resolution[0]:
                img_clip = img_clip.resize(width=self.resolution[0])
            
            img_clip = img_clip.set_duration(duration)
            
            # Apply Ken Burns
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
    
    def get_ffmpeg_params(self) -> Tuple[str, list]:
        """
        Get MoviePy-compatible FFmpeg parameters
        
        MoviePy limitation: Cannot pass -vaapi_device, must use environment
        
        Returns:
            (codec, ffmpeg_params_list)
        """
        if self.gpu_available:
            if self.use_vaapi:
                # CRITICAL: MoviePy doesn't support -vaapi_device
                # Must rely on environment variables and default device
                codec = 'h264_vaapi'
                params = [
                    '-vf', 'format=nv12|vaapi,hwupload',
                    '-qp', '26',
                    '-movflags', '+faststart'
                ]
                
                # Set environment for VAAPI
                os.environ['LIBVA_DRIVER_NAME'] = 'iHD'
                os.environ['LIBVA_DRIVERS_PATH'] = '/usr/lib/x86_64-linux-gnu/dri'
                
                logger.debug("Using VAAPI encoding (environment-based)")
            else:
                codec = 'h264_qsv'
                params = [
                    '-global_quality', '26',
                    '-preset', 'veryfast',
                    '-pix_fmt', 'nv12',
                    '-movflags', '+faststart'
                ]
                logger.debug("Using QSV encoding")
        else:
            codec = 'libx264'
            params = [
                '-crf', str(config.CRF),
                '-preset', config.MOVIEPY_PRESET,
                '-pix_fmt', 'yuv420p',
                '-movflags', '+faststart',
                '-tune', 'fastdecode',
                '-x264-params', 'ref=2:bframes=1:me=hex:subme=2:trellis=0'
            ]
            logger.debug("Using CPU encoding")
        
        return codec, params
    
    def render_with_vaapi_workaround(
        self,
        final_clip: VideoClip,
        output_path: str,
        temp_path: str
    ) -> str:
        """
        Workaround: Render to temp with CPU, then transcode with VAAPI
        
        This is slower but works with MoviePy's limitations
        """
        logger.info("Using VAAPI workaround (2-pass)")
        
        # Pass 1: Render with CPU to temp
        logger.info("Pass 1: CPU rendering to temp file...")
        final_clip.write_videofile(
            temp_path,
            fps=config.DEFAULT_FPS,
            codec='libx264',
            audio_codec=config.DEFAULT_AUDIO_CODEC,
            threads=config.MOVIEPY_THREADS,
            logger=None,
            verbose=False,
            ffmpeg_params=['-crf', '18', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p']
        )
        
        # Pass 2: Transcode with VAAPI
        logger.info("Pass 2: VAAPI transcoding...")
        result = subprocess.run(
            [
                'ffmpeg', '-y',
                '-hwaccel', 'vaapi',
                '-hwaccel_device', '/dev/dri/renderD128',
                '-hwaccel_output_format', 'vaapi',
                '-i', temp_path,
                '-vf', 'scale_vaapi=format=nv12',
                '-c:v', 'h264_vaapi',
                '-qp', '26',
                '-c:a', 'copy',
                '-movflags', '+faststart',
                output_path
            ],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            logger.error(f"VAAPI transcode failed: {result.stderr}")
            raise RuntimeError(f"VAAPI transcode failed: {result.stderr}")
        
        # Cleanup temp
        Path(temp_path).unlink(missing_ok=True)
        
        logger.info("✓ VAAPI 2-pass completed")
        return output_path
    
    def assemble_video(
        self,
        slides: List[Slide],
        output_path: str,
        words_per_slide: List[List[dict]] = None
    ) -> str:
        """Assemble final video with GPU acceleration"""
        logger.info(f"Assembling video: {len(slides)} slides")
        
        slide_clips = []
        
        try:
            # Process slides
            for i, slide in enumerate(slides):
                logger.info(f"Processing slide {i+1}/{len(slides)}")
                
                duration = max(slide.duration, config.MIN_SLIDE_DURATION)
                clip = self.create_slide_clip(slide.image_path, slide.audio_path, duration)
                
                # Add subtitles
                if words_per_slide and i < len(words_per_slide) and words_per_slide[i]:
                    logger.info(f"Adding {len(words_per_slide[i])} word subtitles")
                    clip = render_subtitles(clip, words_per_slide[i], self.resolution)
                
                slide_clips.append(clip)
                
                # GC every N slides
                if config.GC_COLLECT_AFTER_SLIDE and (i + 1) % config.GC_COLLECT_INTERVAL == 0:
                    gc.collect()
            
            logger.info("Applying transitions")
            final_clip = apply_transitions(slide_clips)
            
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # VAAPI requires workaround with MoviePy
            if self.gpu_available and self.use_vaapi:
                logger.info("Using VAAPI 2-pass workaround")
                temp_path = str(Path(output_path).with_suffix('.temp.mp4'))
                try:
                    result = self.render_with_vaapi_workaround(
                        final_clip,
                        output_path,
                        temp_path
                    )
                    
                    # Cleanup
                    final_clip.close()
                    for clip in slide_clips:
                        try:
                            clip.close()
                        except:
                            pass
                    gc.collect()
                    
                    return result
                    
                except Exception as e:
                    logger.warning(f"VAAPI workaround failed: {e}")
                    Path(temp_path).unlink(missing_ok=True)
                    self.gpu_available = False
                    logger.info("Falling back to CPU encoding")
                    # Fall through to CPU
            
            # Standard rendering (QSV or CPU)
            codec, ffmpeg_params = self.get_ffmpeg_params()
            
            logger.info(f"Rendering video with {codec}: {output_path}")
            
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
                if self.gpu_available:
                    logger.warning(f"GPU encoding failed, falling back to CPU: {e}")
                    self.gpu_available = False
                    codec, ffmpeg_params = self.get_ffmpeg_params()
                    
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
            try:
                for clip in slide_clips:
                    clip.close()
            except:
                pass
            gc.collect()