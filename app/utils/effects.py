"""
Effects Helper - Ken Burns and Transitions (CLEAN WORKING VERSION)
"""
import random
import subprocess
from pathlib import Path
from typing import Dict, Tuple, List
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from utils.logger import get_logger

logger = get_logger(__name__)


class KenBurnsEffect:
    """Ken Burns effect - smooth zoom/pan"""
    
    @staticmethod
    def generate_params() -> Dict:
        """Generate random Ken Burns parameters"""
        direction = random.choice(config.KEN_BURNS_DIRECTIONS)
        
        zoom_start = random.uniform(*config.KEN_BURNS_ZOOM_RANGE)
        zoom_end = random.uniform(*config.KEN_BURNS_ZOOM_RANGE)
        
        if abs(zoom_end - zoom_start) < 0.05:
            zoom_end = zoom_start + 0.1
        
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
        Build smooth Ken Burns filter
        Scale to 4000px before zoompan to prevent jitter
        """
        if params is None:
            params = KenBurnsEffect.generate_params()
        
        width, height = resolution
        total_frames = int(duration * fps)
        
        direction = params['direction']
        z_start = params['zoom_start']
        z_end = params['zoom_end']
        
        # Smooth zoom using output frame number
        zoom_expr = f"{z_start}+({z_end}-{z_start})*on/{total_frames}"
        
        # Center by default
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"
        
        # Apply pan
        if direction == "pan_left":
            x_expr = f"iw/2-(iw/zoom/2)+iw*{params['pan_x']}*(1-on/{total_frames})"
        elif direction == "pan_right":
            x_expr = f"iw/2-(iw/zoom/2)-iw*{params['pan_x']}*(1-on/{total_frames})"
        elif direction == "pan_up":
            y_expr = f"ih/2-(ih/zoom/2)+ih*{params['pan_y']}*(1-on/{total_frames})"
        elif direction == "pan_down":
            y_expr = f"ih/2-(ih/zoom/2)-ih*{params['pan_y']}*(1-on/{total_frames})"
        
        # 4000px scaling prevents jitter, faster than 8000px
        kb_filter = (
            f"scale=4000:-1:flags=lanczos,"
            f"zoompan="
            f"z='{zoom_expr}':"
            f"x='{x_expr}':"
            f"y='{y_expr}':"
            f"d=1:"
            f"s={width}x{height}:"
            f"fps={fps}"
        )
        
        return kb_filter


class CustomTransitions:
    """Working transitions"""
    
    TRANSITIONS = ['glitch', 'flash', 'zoom_punch']
    
    @staticmethod
    def get_random_transition() -> str:
        return random.choice(CustomTransitions.TRANSITIONS)
    
    @staticmethod
    def apply_glitch_transition(
        clip1_path: str,
        clip2_path: str,
        output_path: str,
        duration: float = 0.3
    ) -> str:
        """
        RGB Glitch - apply ONLY to transition section
        Uses split+trim+concat to apply geq only to last/first seconds
        """
        logger.info("Applying glitch transition")
        
        def get_duration(path):
            cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                   '-of', 'default=noprint_wrappers=1:nokey=1', path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return float(result.stdout.strip())
        
        clip1_dur = get_duration(clip1_path)
        clip2_dur = get_duration(clip2_path)
        offset = clip1_dur - duration
        
        shift = 8
        
        # Split clips, apply geq only to transition parts, then concat
        filter_complex = (
            # Clip1: split into normal part + glitched part
            f"[0:v]split=2[c1_normal][c1_glitch];"
            f"[c1_normal]trim=end={offset},setpts=PTS-STARTPTS[c1_pre];"
            f"[c1_glitch]trim=start={offset},setpts=PTS-STARTPTS,"
            f"geq=r='r(X-{shift},Y)':g='g(X,Y)':b='b(X+{shift},Y)'[c1_post];"
            f"[c1_pre][c1_post]concat=n=2:v=1:a=0[v1];"
            
            # Clip2: split into glitched part + normal part  
            f"[1:v]split=2[c2_glitch][c2_normal];"
            f"[c2_glitch]trim=end={duration},setpts=PTS-STARTPTS,"
            f"geq=r='r(X+{shift},Y)':g='g(X,Y)':b='b(X-{shift},Y)'[c2_pre];"
            f"[c2_normal]trim=start={duration},setpts=PTS-STARTPTS[c2_post];"
            f"[c2_pre][c2_post]concat=n=2:v=1:a=0[v2];"
            
            # Crossfade between clips
            f"[v1][v2]xfade=transition=fade:duration={duration}:offset={offset}[v]"
        )
        
        cmd = [
            'ffmpeg', '-y',
            '-i', clip1_path,
            '-i', clip2_path,
            '-filter_complex', f"{filter_complex};[0:a][1:a]acrossfade=d={duration}[a]",
            '-map', '[v]',
            '-map', '[a]',
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '20',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac',
            '-shortest',
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            logger.error(f"Glitch failed: {result.stderr[-1000:]}")
            raise RuntimeError("Glitch transition failed")
        
        return output_path
    
    @staticmethod
    def apply_flash_transition(
        clip1_path: str,
        clip2_path: str,
        output_path: str,
        duration: float = 0.3
    ) -> str:
        """White flash transition"""
        logger.info("Applying flash transition")
        
        def get_duration(path):
            cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                   '-of', 'default=noprint_wrappers=1:nokey=1', path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return float(result.stdout.strip())
        
        clip1_dur = get_duration(clip1_path)
        offset = clip1_dur - duration
        
        filter_complex = (
            f"[0:v]fade=t=out:st={offset}:d={duration}:color=white[v1];"
            f"[1:v]fade=t=in:st=0:d={duration}:color=white[v2];"
            f"[v1][v2]xfade=transition=fade:duration={duration}:offset={offset}[v]"
        )
        
        cmd = [
            'ffmpeg', '-y',
            '-i', clip1_path,
            '-i', clip2_path,
            '-filter_complex', f"{filter_complex};[0:a][1:a]acrossfade=d={duration}[a]",
            '-map', '[v]',
            '-map', '[a]',
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '20',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac',
            '-shortest',
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            logger.error(f"Flash failed: {result.stderr[-1000:]}")
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
        Zoom punch - quick zoom in at end of clip1
        Uses pzoom for video clips (key discovery from Stack Overflow)
        """
        logger.info("Applying zoom punch transition")
        
        def get_duration(path):
            cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                   '-of', 'default=noprint_wrappers=1:nokey=1', path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return float(result.stdout.strip())
        
        def get_resolution(path):
            cmd = ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                   '-show_entries', 'stream=width,height',
                   '-of', 'csv=p=0', path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            w, h = result.stdout.strip().split(',')
            return int(w), int(h)
        
        def get_fps(path):
            cmd = ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                   '-show_entries', 'stream=r_frame_rate',
                   '-of', 'csv=p=0', path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            num, den = result.stdout.strip().split('/')
            return int(num) / int(den)
        
        clip1_dur = get_duration(clip1_path)
        width, height = get_resolution(clip1_path)
        fps = get_fps(clip1_path)
        offset = clip1_dur - duration
        
        zoom_frames = int(duration * fps)
        zoom_increment = 0.5 / zoom_frames  # Zoom from 1.0 to 1.5
        
        # Apply zoompan to clip1 - zoom in during last seconds
        # KEY: use pzoom (previous zoom) and d=1 for video clips
        filter_complex = (
            f"[0:v]zoompan="
            f"z='pzoom+{zoom_increment}':"
            f"x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':"
            f"d=1:"
            f"s={width}x{height}:"
            f"fps={int(fps)}[v1];"
            
            f"[1:v]copy[v2];"
            
            f"[v1][v2]xfade=transition=fade:duration={duration}:offset={offset}[v]"
        )
        
        cmd = [
            'ffmpeg', '-y',
            '-i', clip1_path,
            '-i', clip2_path,
            '-filter_complex', f"{filter_complex};[0:a][1:a]acrossfade=d={duration}[a]",
            '-map', '[v]',
            '-map', '[a]',
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '20',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac',
            '-shortest',
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            logger.error(f"Zoom punch failed: {result.stderr[-1000:]}")
            raise RuntimeError("Zoom punch failed")
        
        return output_path


class SubtitleEffect:
    """Subtitle rendering with smooth fade"""
    
    @staticmethod
    def create_srt_file(words: list, output_path: str) -> str:
        """Create SRT subtitle file"""
        if not words:
            return None
        
        srt_lines = []
        
        for i, word_data in enumerate(words, 1):
            word = word_data['word'].strip()
            if not word:
                continue
            
            start = word_data['start']
            end = word_data['end']
            
            def format_time(seconds):
                hours = int(seconds // 3600)
                minutes = int((seconds % 3600) // 60)
                secs = int(seconds % 60)
                millis = int((seconds % 1) * 1000)
                return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
            
            srt_lines.append(f"{i}")
            srt_lines.append(f"{format_time(start)} --> {format_time(end)}")
            srt_lines.append(word)
            srt_lines.append("")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(srt_lines))
        
        return output_path
    
    @staticmethod
    def build_subtitle_filter(words: List[dict], resolution: Tuple[int, int]) -> str:
        """Build drawtext filter with smooth fade in/out"""
        if not words:
            return ""
        
        font_size = config.SUBTITLE_FONT_SIZE
        drawtext_filters = []
        
        FADE_DURATION = 0.1  # 100ms fade
        MIN_GAP = 0.05  # 50ms gap between words
        
        prev_end = 0.0
        
        for word_data in words:
            word = word_data['word'].strip()
            if not word:
                continue
            
            start = word_data['start']
            end = word_data['end']
            
            # Ensure no overlap
            if start < prev_end + MIN_GAP:
                start = prev_end + MIN_GAP
            
            # Minimum display time
            if end - start < 0.15:
                end = start + 0.15
            
            word_escaped = word.replace('\\', '\\\\').replace("'", "'\\''").replace(':', '\\:').replace('%', '\\%')
            
            # Smooth fade using alpha expression
            fade_in_end = start + FADE_DURATION
            fade_out_start = end - FADE_DURATION
            
            # Build alpha expression for fade
            alpha_expr = (
                f"if(lt(t,{start:.3f}),0,"
                f"if(lt(t,{fade_in_end:.3f}),(t-{start:.3f})/{FADE_DURATION},"
                f"if(lt(t,{fade_out_start:.3f}),1,"
                f"if(lt(t,{end:.3f}),({end:.3f}-t)/{FADE_DURATION},0))))"
            )
            
            drawtext = (
                f"drawtext="
                f"text='{word_escaped}':"
                f"fontsize={font_size}:"
                f"fontcolor=white:"
                f"borderw=5:"
                f"bordercolor=black:"
                f"x=(w-text_w)/2:"
                f"y=(h-text_h)/2:"
                f"alpha='{alpha_expr}'"
            )
            drawtext_filters.append(drawtext)
            
            prev_end = end
        
        return ",".join(drawtext_filters) if drawtext_filters else ""