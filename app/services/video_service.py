"""
Video Service - Fixed Frame Count Issue
"""
import subprocess
import random
from pathlib import Path
from typing import List, Tuple, Dict
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from models.slide import Slide
from utils.logger import get_logger
from pydub import AudioSegment

logger = get_logger(__name__)


class VideoService:
    """Fast video generation with FFmpeg"""
    
    def __init__(self, resolution: Tuple[int, int]):
        self.resolution = resolution
        self.fps = config.DEFAULT_FPS
        logger.info(f"VideoService: {resolution[0]}x{resolution[1]} @ {self.fps}fps")
    
    def build_subtitle_filter(self, words: List[Dict], start_offset: float) -> str:
        """Build drawtext filter for word-by-word subtitles"""
        if not words:
            return ""
        
        font_file = "/usr/share/fonts/truetype/montserrat/Montserrat-Bold.ttf"
        font_size = config.SUBTITLE_FONT_SIZE
        
        drawtext_filters = []
        for word_data in words:
            word = word_data['word'].strip()
            if not word:
                continue
            
            start = word_data['start'] - start_offset
            end = word_data['end'] - start_offset
            
            # Escape special characters
            word_escaped = (word
                .replace("\\", "\\\\")
                .replace("'", "'\\\\\\''")
                .replace(":", "\\:")
                .replace("%", "\\%"))
            
            drawtext = (
                f"drawtext="
                f"fontfile='{font_file}':"
                f"text='{word_escaped}':"
                f"fontsize={font_size}:"
                f"fontcolor=white:"
                f"borderw=5:"
                f"bordercolor=black:"
                f"x=(w-text_w)/2:"
                f"y=(h-text_h)/2:"
                f"enable='between(t,{start:.3f},{end:.3f})'"
            )
            drawtext_filters.append(drawtext)
        
        return ",".join(drawtext_filters) if drawtext_filters else ""
    
    def build_ken_burns_filter(self, duration: float) -> str:
        """Build zoompan filter for Ken Burns effect"""
        direction = random.choice(config.KEN_BURNS_DIRECTIONS)
        zoom_start = random.uniform(*config.KEN_BURNS_ZOOM_RANGE)
        zoom_end = random.uniform(*config.KEN_BURNS_ZOOM_RANGE)
        
        if direction == "zoom_out":
            zoom_start, zoom_end = max(zoom_start, zoom_end), min(zoom_start, zoom_end)
        
        # CRITICAL: Calculate exact number of frames needed
        total_frames = int(duration * self.fps)
        
        # Simplified zoom expression
        zoom_expr = f"'if(lte(zoom,1.0),{zoom_start},min(zoom+{(zoom_end-zoom_start)/total_frames},{zoom_end}))'"
        
        zoompan = (
            f"zoompan="
            f"z={zoom_expr}:"
            f"d={total_frames}:"  # EXACT frame count
            f"x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':"
            f"s={self.resolution[0]}x{self.resolution[1]}:"
            f"fps={self.fps}"
        )
        
        return zoompan
    
    def build_filter_complex(
        self,
        slides: List[Slide],
        words_per_slide: List[List[Dict]],
        use_vaapi: bool
    ) -> str:
        """Build complete filter_complex string"""
        filter_parts = []
        stream_labels = []
        
        current_time = 0.0
        
        for i, slide in enumerate(slides):
            duration = max(slide.duration, config.MIN_SLIDE_DURATION)
            words = words_per_slide[i] if i < len(words_per_slide) else []
            
            input_label = f"[{i}:v]"
            
            # Calculate exact frames for this slide
            num_frames = int(duration * self.fps)
            
            # Scale to fit resolution (keeping aspect ratio)
            scale_filter = (
                f"{input_label}"
                f"scale={self.resolution[0]}:{self.resolution[1]}:force_original_aspect_ratio=increase,"
                f"crop={self.resolution[0]}:{self.resolution[1]},"
                f"setsar=1"
            )
            
            # Ken Burns with EXACT frame count
            kb_filter = self.build_ken_burns_filter(duration)
            scale_filter += f",{kb_filter}"
            
            # Set PTS to start from 0
            scale_filter += ",setpts=PTS-STARTPTS"
            
            # Trim to exact duration (prevents extra frames)
            scale_filter += f",trim=duration={duration}"
            
            # Subtitles
            subtitle_filter = self.build_subtitle_filter(words, current_time)
            if subtitle_filter:
                scale_filter += f",{subtitle_filter}"
            
            output_label = f"[v{i}]"
            scale_filter += output_label
            
            filter_parts.append(scale_filter)
            stream_labels.append(f"v{i}")
            
            current_time += duration
        
        # Concatenate videos
        concat_inputs = "".join(f"[{label}]" for label in stream_labels)
        concat_filter = f"{concat_inputs}concat=n={len(slides)}:v=1:a=0[vtmp]"
        filter_parts.append(concat_filter)
        
        # Hardware upload for VAAPI
        if use_vaapi:
            hwupload_filter = "[vtmp]format=nv12,hwupload[vout]"
            filter_parts.append(hwupload_filter)
        else:
            filter_parts.append("[vtmp]copy[vout]")
        
        # Concatenate audio
        audio_inputs = "".join(f"[{i+len(slides)}:a]" for i in range(len(slides)))
        audio_concat = f"{audio_inputs}concat=n={len(slides)}:v=0:a=1[aout]"
        filter_parts.append(audio_concat)
        
        return ";".join(filter_parts)
    
    def detect_vaapi(self) -> bool:
        """Check VAAPI availability"""
        try:
            result = subprocess.run(['vainfo'], capture_output=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def assemble_video(
        self,
        slides: List[Slide],
        output_path: str,
        words_per_slide: List[List[dict]] = None
    ) -> str:
        """
        Assemble video with FFmpeg filter_complex
        FIXED: Proper frame count to avoid infinite loops
        """
        logger.info(f"Assembling video: {len(slides)} slides")
        
        try:
            # Validate
            if not slides:
                raise ValueError("No slides provided")
            
            for i, slide in enumerate(slides):
                if not Path(slide.image_path).exists():
                    raise FileNotFoundError(f"Slide {i} image not found: {slide.image_path}")
                if not Path(slide.audio_path).exists():
                    raise FileNotFoundError(f"Slide {i} audio not found: {slide.audio_path}")
            
            # Check VAAPI
            use_vaapi = self.detect_vaapi()
            
            # Build filter_complex
            filter_complex = self.build_filter_complex(slides, words_per_slide or [], use_vaapi)
            
            # Build FFmpeg command
            cmd = ['ffmpeg', '-y']
            
            # VAAPI device initialization
            if use_vaapi:
                logger.info("🚀 Using VAAPI GPU encoding")
                cmd.extend([
                    '-init_hw_device', 'vaapi=va:/dev/dri/renderD128',
                    '-filter_hw_device', 'va'
                ])
            else:
                logger.info("💻 Using CPU encoding")
            
            # FIXED: Input images WITHOUT loop, using framerate to control duration
            for slide in slides:
                duration = max(slide.duration, config.MIN_SLIDE_DURATION)
                num_frames = int(duration * self.fps)
                
                # Use -t with -loop 1, but filter_complex will trim
                cmd.extend([
                    '-loop', '1',
                    '-t', str(duration),  # Limit input duration
                    '-i', slide.image_path
                ])
            
            # Input audio
            for slide in slides:
                cmd.extend(['-i', slide.audio_path])
            
            # Filter complex with trim
            cmd.extend(['-filter_complex', filter_complex])
            
            # Map outputs
            cmd.extend(['-map', '[vout]', '-map', '[aout]'])
            
            # Video encoding
            if use_vaapi:
                cmd.extend([
                    '-c:v', 'h264_vaapi',
                    '-qp', str(config.CRF)
                ])
            else:
                cmd.extend([
                    '-c:v', 'libx264',
                    '-crf', str(config.CRF),
                    '-preset', config.MOVIEPY_PRESET,
                    '-tune', 'fastdecode',
                    '-pix_fmt', 'yuv420p'
                ])
            
            # Audio encoding
            cmd.extend([
                '-c:a', 'aac',
                '-b:a', '192k',
                '-ar', '48000'
            ])
            
            # Output with exact duration check
            total_duration = sum(max(s.duration, config.MIN_SLIDE_DURATION) for s in slides)
            cmd.extend([
                '-t', str(total_duration),  # Force exact output duration
                '-movflags', '+faststart',
                output_path
            ])
            
            # Log command
            logger.info(f"Expected video duration: {total_duration:.2f}s")
            logger.debug(f"FFmpeg command: {' '.join(cmd[:20])}... (total {len(cmd)} args)")
            
            # Execute
            logger.info("Starting FFmpeg encoding...")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode != 0:
                logger.error(f"FFmpeg stderr:\n{result.stderr}")
                raise RuntimeError(f"FFmpeg failed (code {result.returncode})")
            
            # Verify output
            if not Path(output_path).exists():
                raise RuntimeError("Output file not created")
            
            file_size = Path(output_path).stat().st_size / (1024 * 1024)
            logger.info(f"✓ Video assembled: {file_size:.2f} MB")
            
            return output_path
            
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg timeout (>10 minutes)")
            raise RuntimeError("Encoding timeout")
        except Exception as e:
            logger.error(f"Failed to assemble video: {e}", exc_info=True)
            raise