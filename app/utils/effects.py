"""
Effects Helper - Ken Burns and Custom Transitions (Glitch, Flash, Zoom Punch)
Save this as: app/utils/effects.py
"""
import random
import subprocess
import numpy as np
from pathlib import Path
from typing import Dict, Tuple, List
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from utils.logger import get_logger

logger = get_logger(__name__)


class KenBurnsEffect:
    """Ken Burns effect generator for FFmpeg"""
    
    @staticmethod
    def generate_params() -> Dict:
        """Generate random Ken Burns parameters"""
        direction = random.choice(config.KEN_BURNS_DIRECTIONS)
        
        zoom_start = random.uniform(*config.KEN_BURNS_ZOOM_RANGE)
        zoom_end = random.uniform(*config.KEN_BURNS_ZOOM_RANGE)
        
        # Ensure minimum zoom difference
        if abs(zoom_end - zoom_start) < 0.1:
            zoom_end = zoom_start + 0.15
        
        # Swap for zoom_out
        if direction == "zoom_out":
            zoom_start, zoom_end = max(zoom_start, zoom_end), min(zoom_start, zoom_end)
        
        pan_x = random.uniform(*config.KEN_BURNS_PAN_RANGE)
        pan_y = random.uniform(*config.KEN_BURNS_PAN_RANGE)
        
        params = {
            'direction': direction,
            'zoom_start': zoom_start,
            'zoom_end': zoom_end,
            'pan_x': pan_x,
            'pan_y': pan_y
        }
        
        logger.debug(f"Ken Burns: {params}")
        return params
    
    @staticmethod
    def build_filter(
        duration: float,
        fps: int,
        resolution: Tuple[int, int],
        params: Dict = None
    ) -> str:
        """
        Build FFmpeg zoompan filter for Ken Burns effect
        WITHOUT input/output labels (to be added by caller)
        
        Args:
            duration: Clip duration in seconds
            fps: Frames per second
            resolution: (width, height)
            params: Ken Burns parameters (auto-generated if None)
            
        Returns:
            FFmpeg zoompan filter string (without labels)
        """
        if params is None:
            params = KenBurnsEffect.generate_params()
        
        total_frames = int(duration * fps)
        direction = params['direction']
        zoom_start = params['zoom_start']
        zoom_end = params['zoom_end']
        pan_x = params['pan_x']
        pan_y = params['pan_y']
        
        width, height = resolution
        
        # Smooth zoom interpolation
        zoom_expr = f"'if(eq(on,1),{zoom_start},{zoom_start}+({zoom_end}-{zoom_start})*on/{total_frames})'"
        
        # Pan expressions based on direction
        if direction == "pan_left":
            x_expr = f"'iw/2-(iw/zoom/2)+({pan_x}*iw)*(on/{total_frames})'"
            y_expr = "'ih/2-(ih/zoom/2)'"
        elif direction == "pan_right":
            x_expr = f"'iw/2-(iw/zoom/2)-({pan_x}*iw)*(on/{total_frames})'"
            y_expr = "'ih/2-(ih/zoom/2)'"
        elif direction == "pan_up":
            x_expr = "'iw/2-(iw/zoom/2)'"
            y_expr = f"'ih/2-(ih/zoom/2)+({pan_y}*ih)*(on/{total_frames})'"
        elif direction == "pan_down":
            x_expr = "'iw/2-(iw/zoom/2)'"
            y_expr = f"'ih/2-(ih/zoom/2)-({pan_y}*ih)*(on/{total_frames})'"
        else:  # zoom_in or zoom_out
            x_expr = "'iw/2-(iw/zoom/2)'"
            y_expr = "'ih/2-(ih/zoom/2)'"
        
        zoompan = (
            f"zoompan="
            f"z={zoom_expr}:"
            f"x={x_expr}:"
            f"y={y_expr}:"
            f"d={total_frames}:"
            f"s={width}x{height}:"
            f"fps={fps}"
        )
        
        return zoompan


class CustomTransitions:
    """Custom transitions: Glitch, Flash, Zoom Punch"""
    
    TRANSITIONS = ['glitch', 'flash', 'zoom_punch']
    
    @staticmethod
    def get_random_transition() -> str:
        """Get random transition from custom set"""
        return random.choice(CustomTransitions.TRANSITIONS)
    
    @staticmethod
    def apply_glitch_transition(
        clip1_path: str,
        clip2_path: str,
        output_path: str,
        duration: float = 0.3
    ) -> str:
        """
        Apply glitch transition using FFmpeg complex filters
        
        Creates RGB channel shift effect at the end of clip1 and start of clip2
        """
        logger.info("Applying glitch transition")
        
        # Get clip durations
        def get_duration(path):
            cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                   '-of', 'default=noprint_wrappers=1:nokey=1', path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return float(result.stdout.strip())
        
        clip1_dur = get_duration(clip1_path)
        clip2_dur = get_duration(clip2_path)
        
        # Glitch parameters
        glitch_start1 = clip1_dur - duration
        shift_amount = 30  # pixels
        
        # Build complex filter for glitch effect
        # For clip1 (end): shift red and blue channels
        filter_complex = (
            # Load both clips
            f"[0:v]split=3[r1][g1][b1];"
            f"[1:v]split=3[r2][g2][b2];"
            
            # Clip1 glitch (last {duration} seconds): shift channels
            f"[r1]crop=iw-{shift_amount}:ih:{shift_amount}:0,pad=iw+{shift_amount}:ih:0:0:black[r1s];"
            f"[b1]crop=iw-{shift_amount}:ih:0:0,pad=iw+{shift_amount}:ih:{shift_amount}:0:black[b1s];"
            f"[r1s][g1][b1s]mergeplanes=0x001020:rgb[clip1glitch];"
            
            # Clip2 glitch (first {duration} seconds): horizontal slice shifts
            f"[r2]crop=iw-{shift_amount}:ih:{shift_amount}:0,pad=iw+{shift_amount}:ih:0:0:black[r2s];"
            f"[b2]crop=iw-{shift_amount}:ih:0:0,pad=iw+{shift_amount}:ih:{shift_amount}:0:black[b2s];"
            f"[r2s][g2][b2s]mergeplanes=0x001020:rgb[clip2glitch];"
            
            # Fade transition between glitched clips
            f"[clip1glitch][clip2glitch]xfade=transition=fade:duration={duration}:offset={glitch_start1}[v]"
        )
        
        cmd = [
            'ffmpeg', '-y',
            '-i', clip1_path,
            '-i', clip2_path,
            '-filter_complex', filter_complex,
            '-map', '[v]',
            '-c:v', 'libx264',
            '-preset', config.MOVIEPY_PRESET,
            '-crf', str(config.CRF),
            '-pix_fmt', 'yuv420p',
            '-t', str(clip1_dur + clip2_dur),
            output_path
        ]
        
        # Merge audio with crossfade
        cmd.insert(-6, '-filter_complex')
        cmd.insert(-6, f"{filter_complex};[0:a][1:a]acrossfade=d={duration}[a]")
        cmd.insert(-4, '-map')
        cmd.insert(-4, '[a]')
        cmd.insert(-2, '-c:a')
        cmd.insert(-2, 'aac')
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            logger.error(f"Glitch transition failed: {result.stderr[-500:]}")
            raise RuntimeError("Glitch transition failed")
        
        return output_path
    
    @staticmethod
    def apply_flash_transition(
        clip1_path: str,
        clip2_path: str,
        output_path: str,
        duration: float = 0.3
    ) -> str:
        """
        Apply flash transition using FFmpeg
        
        Brightens to white at end of clip1, then fades from white in clip2
        """
        logger.info("Applying flash transition")
        
        def get_duration(path):
            cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                   '-of', 'default=noprint_wrappers=1:nokey=1', path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return float(result.stdout.strip())
        
        clip1_dur = get_duration(clip1_path)
        flash_start = clip1_dur - duration
        
        # Build flash effect with curves and zoom
        filter_complex = (
            # Clip1: fade to white + zoom at end
            f"[0:v]eq=brightness=0.4:saturation=0.8,"
            f"fade=t=out:st={flash_start}:d={duration}:color=white,"
            f"zoompan=z='if(gte(on,{int(flash_start*config.DEFAULT_FPS)}),1+0.5*(on-{int(flash_start*config.DEFAULT_FPS)})/{int(duration*config.DEFAULT_FPS)},1)':"
            f"d=1:s={{w}}x{{h}}:fps={config.DEFAULT_FPS}[v1];"
            
            # Clip2: fade from white
            f"[1:v]fade=t=in:st=0:d={duration}:color=white[v2];"
            
            # Concatenate
            f"[v1][v2]concat=n=2:v=1:a=0[v]"
        )
        
        cmd = [
            'ffmpeg', '-y',
            '-i', clip1_path,
            '-i', clip2_path,
            '-filter_complex', f"{filter_complex};[0:a][1:a]acrossfade=d={duration}[a]",
            '-map', '[v]',
            '-map', '[a]',
            '-c:v', 'libx264',
            '-preset', config.MOVIEPY_PRESET,
            '-crf', str(config.CRF),
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac',
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            logger.error(f"Flash transition failed: {result.stderr[-500:]}")
            raise RuntimeError("Flash transition failed")
        
        return output_path
    
    @staticmethod
    def apply_zoom_punch_transition(
        clip1_path: str,
        clip2_path: str,
        output_path: str,
        duration: float = 0.3
    ) -> str:
        """
        Apply aggressive zoom punch transition
        
        Zooms in aggressively at end of clip1
        """
        logger.info("Applying zoom punch transition")
        
        def get_duration(path):
            cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                   '-of', 'default=noprint_wrappers=1:nokey=1', path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return float(result.stdout.strip())
        
        clip1_dur = get_duration(clip1_path)
        zoom_start = clip1_dur - duration
        fps = config.DEFAULT_FPS
        zoom_frames = int(duration * fps)
        zoom_start_frame = int(zoom_start * fps)
        
        # Aggressive zoom with quadratic acceleration
        filter_complex = (
            f"[0:v]zoompan="
            f"z='if(lte(on,{zoom_start_frame}),1,1+3*pow((on-{zoom_start_frame})/{zoom_frames},2))':"
            f"d=1:s={{w}}x{{h}}:fps={fps}[v1];"
            
            # Clip2 normal
            f"[1:v]copy[v2];"
            
            # Quick fade transition
            f"[v1][v2]xfade=transition=fade:duration=0.1:offset={clip1_dur-0.1}[v]"
        )
        
        cmd = [
            'ffmpeg', '-y',
            '-i', clip1_path,
            '-i', clip2_path,
            '-filter_complex', f"{filter_complex};[0:a][1:a]acrossfade=d=0.1[a]",
            '-map', '[v]',
            '-map', '[a]',
            '-c:v', 'libx264',
            '-preset', config.MOVIEPY_PRESET,
            '-crf', str(config.CRF),
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac',
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            logger.error(f"Zoom punch transition failed: {result.stderr[-500:]}")
            raise RuntimeError("Zoom punch transition failed")
        
        return output_path


class SubtitleEffect:
    """Subtitle rendering for FFmpeg"""
    
    @staticmethod
    def create_srt_file(words: list, output_path: str) -> str:
        """
        Create SRT subtitle file from word timestamps
        
        Args:
            words: List of {word, start, end} dictionaries
            output_path: Path to save SRT file
            
        Returns:
            Path to created SRT file
        """
        if not words:
            return None
        
        srt_lines = []
        
        for i, word_data in enumerate(words, 1):
            word = word_data['word'].strip()
            if not word:
                continue
            
            start = word_data['start']
            end = word_data['end']
            
            # Convert to SRT timestamp format: HH:MM:SS,mmm
            def format_time(seconds):
                hours = int(seconds // 3600)
                minutes = int((seconds % 3600) // 60)
                secs = int(seconds % 60)
                millis = int((seconds % 1) * 1000)
                return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
            
            srt_lines.append(f"{i}")
            srt_lines.append(f"{format_time(start)} --> {format_time(end)}")
            srt_lines.append(word)
            srt_lines.append("")  # Blank line between entries
        
        # Write SRT file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(srt_lines))
        
        logger.debug(f"Created SRT file: {output_path} ({len(words)} words)")
        return output_path
    
    @staticmethod
    def build_subtitle_filter(srt_path: str, font_size: int = None) -> str:
        """
        Build FFmpeg subtitles filter
        
        Args:
            srt_path: Path to SRT file
            font_size: Font size (uses config default if None)
            
        Returns:
            FFmpeg subtitles filter string
        """
        if not srt_path or not Path(srt_path).exists():
            return ""
        
        if font_size is None:
            font_size = config.SUBTITLE_FONT_SIZE
        
        # Escape path for FFmpeg
        srt_escaped = str(srt_path).replace('\\', '/').replace(':', '\\:')
        
        # ASS style for subtitles
        style = (
            f"FontName=Montserrat Bold,"
            f"FontSize={font_size},"
            f"PrimaryColour=&HFFFFFF&,"  # White
            f"OutlineColour=&H000000&,"  # Black outline
            f"BorderStyle=1,"
            f"Outline=5,"
            f"Shadow=0,"
            f"Alignment=2,"  # Center bottom
            f"MarginV=50"
        )
        
        return f"subtitles='{srt_escaped}':force_style='{style}'"