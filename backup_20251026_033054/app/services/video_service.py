"""
Video Service - Direct FFmpeg with filter_complex (MAXIMUM SPEED)
"""
import subprocess
import json
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
    """Ultra-fast video generation with FFmpeg filter_complex"""
    
    def __init__(self, resolution: Tuple[int, int]):
        self.resolution = resolution
        self.fps = config.DEFAULT_FPS
        logger.info(f"VideoService (filter_complex): {resolution[0]}x{resolution[1]} @ {self.fps}fps")
    
    def merge_audio_files(self, audio_paths: List[str], output_path: str) -> str:
        """Merge audio files"""
        try:
            logger.info(f"Merging {len(audio_paths)} audio files")
            combined = AudioSegment.empty()
            for audio_path in audio_paths:
                if Path(audio_path).exists():
                    combined += AudioSegment.from_file(audio_path)
            combined.export(output_path, format="mp3")
            logger.info(f"✓ Audio merged: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Failed to merge audio: {e}")
            raise
    
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
            word_escaped = word.replace("'", r"'\\\''").replace(":", r"\:").replace("%", r"\%")
            
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
        
        total_frames = int(duration * self.fps)
        
        # zoompan: smooth zoom with pan
        zoom_expr = f"'min(zoom+0.001,max(zoom,{zoom_end}))'"
        
        zoompan = (
            f"zoompan="
            f"z={zoom_expr}:"
            f"d={total_frames}:"
            f"x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':"
            f"s={self.resolution[0]}x{self.resolution[1]}:"
            f"fps={self.fps}"
        )
        
        return zoompan
    
    def build_filter_complex(
        self,
        slides: List[Slide],
        words_per_slide: List[List[Dict]]
    ) -> str:
        """Build complete filter_complex string"""
        filter_parts = []
        stream_labels = []
        
        current_time = 0.0
        
        for i, slide in enumerate(slides):
            duration = max(slide.duration, config.MIN_SLIDE_DURATION)
            words = words_per_slide[i] if i < len(words_per_slide) else []
            
            # Input: [i:v]
            input_label = f"[{i}:v]"
            
            # Step 1: Scale to fit resolution
            scale_filter = (
                f"{input_label}"
                f"scale={self.resolution[0]}:{self.resolution[1]}:force_original_aspect_ratio=increase,"
                f"crop={self.resolution[0]}:{self.resolution[1]},"
                f"setsar=1,"
                f"fps={self.fps},"
                f"setpts=PTS-STARTPTS"
            )
            
            # Step 2: Ken Burns
            kb_filter = self.build_ken_burns_filter(duration)
            scale_filter += f",{kb_filter}"
            
            # Step 3: Subtitles
            subtitle_filter = self.build_subtitle_filter(words, current_time)
            if subtitle_filter:
                scale_filter += f",{subtitle_filter}"
            
            output_label = f"[v{i}]"
            scale_filter += output_label
            
            filter_parts.append(scale_filter)
            stream_labels.append(f"v{i}")
            
            current_time += duration
        
        # Concatenate all slides
        concat_inputs = "".join(f"[{label}]" for label in stream_labels)
        concat_filter = f"{concat_inputs}concat=n={len(slides)}:v=1:a=0[vout]"
        filter_parts.append(concat_filter)
        
        # Audio concat
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
        Assemble video with filter_complex (single pass)
        
        5-10x faster than frame-by-frame rendering
        """
        logger.info(f"Assembling video: {len(slides)} slides (filter_complex)")
        
        try:
            # Validate
            if not slides:
                raise ValueError("No slides provided")
            
            for i, slide in enumerate(slides):
                if not Path(slide.image_path).exists():
                    raise FileNotFoundError(f"Slide {i} image not found: {slide.image_path}")
                if not Path(slide.audio_path).exists():
                    raise FileNotFoundError(f"Slide {i} audio not found: {slide.audio_path}")
            
            # Build filter_complex
            filter_complex = self.build_filter_complex(slides, words_per_slide or [])
            
            # Build FFmpeg command
            cmd = ['ffmpeg', '-y']
            
            # Hardware acceleration
            use_vaapi = self.detect_vaapi()
            if use_vaapi:
                logger.info("🚀 Using VAAPI GPU encoding")
                cmd.extend([
                    '-init_hw_device', 'vaapi=va:/dev/dri/renderD128',
                    '-filter_hw_device', 'va'
                ])
            else:
                logger.info("💻 Using CPU encoding")
            
            # Input images (looped)
            for slide in slides:
                duration = max(slide.duration, config.MIN_SLIDE_DURATION)
                cmd.extend([
                    '-loop', '1',
                    '-framerate', str(self.fps),
                    '-t', str(duration),
                    '-i', slide.image_path
                ])
            
            # Input audio
            for slide in slides:
                cmd.extend(['-i', slide.audio_path])
            
            # Filter complex
            cmd.extend(['-filter_complex', filter_complex])
            
            # Map outputs
            cmd.extend(['-map', '[vout]', '-map', '[aout]'])
            
            # Video encoding
            if use_vaapi:
                cmd.extend([
                    '-c:v', 'h264_vaapi',
                    '-qp', str(config.CRF),
                    '-rc_mode', 'CQP'
                ])
            else:
                cmd.extend([
                    '-c:v', 'libx264',
                    '-crf', str(config.CRF),
                    '-preset', config.MOVIEPY_PRESET
                ])
            
            # Audio encoding
            cmd.extend([
                '-c:a', 'aac',
                '-b:a', '192k',
                '-ar', '48000'
            ])
            
            # Output
            cmd.extend([
                '-movflags', '+faststart',
                '-pix_fmt', 'yuv420p',
                '-shortest',
                output_path
            ])
            
            # Log command (truncated)
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
                logger.error(f"FFmpeg stderr: {result.stderr[-1000:]}")
                raise RuntimeError(f"FFmpeg failed: {result.stderr[-500:]}")
            
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