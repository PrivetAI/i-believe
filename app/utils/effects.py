"""
Effects Helper - Ken Burns and Transitions (CapCut-style Dynamic Glitch)
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
    """Working transitions with timebase normalization"""
    
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
        Dynamic CapCut-style Glitch transition
        Multi-layer effect with RGB shift + noise + distortion
        """
        logger.info("Applying DYNAMIC glitch transition (CapCut-style)")
        
        def get_duration(path):
            cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                   '-of', 'default=noprint_wrappers=1:nokey=1', path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return float(result.stdout.strip())
        
        clip1_dur = get_duration(clip1_path)
        offset = clip1_dur - duration
        
        # Dynamic parameters
        rgb_shift = random.randint(8, 15)  # More aggressive shift
        noise_strength = random.uniform(0.02, 0.05)  # Add noise
        
        # Build complex glitch effect with multiple layers
        filter_complex = (
            # === CLIP 1 PROCESSING ===
            # Normalize and split into 3 streams
            f"[0:v]settb=AVTB,fps=30[v0_base];"
            f"[v0_base]split=3[v0a][v0b][v0c];"
            
            # Normal part (before transition)
            f"[v0a]trim=end={offset},setpts=PTS-STARTPTS[v0_pre];"
            
            # Glitched part - Layer 1: RGB shift
            f"[v0b]trim=start={offset},setpts=PTS-STARTPTS,"
            f"geq=r='r(X-{rgb_shift},Y)':g='g(X,Y)':b='b(X+{rgb_shift},Y)'[v0_glitch1];"
            
            # Glitched part - Layer 2: Add noise + random displacement
            f"[v0c]trim=start={offset},setpts=PTS-STARTPTS,"
            f"noise=c0s={int(noise_strength*100)}:allf=t,"
            f"geq=r='r(X+sin(Y/10)*5,Y)':g='g(X,Y)':b='b(X-sin(Y/10)*5,Y)'[v0_glitch2];"
            
            # Blend the two glitch layers
            f"[v0_glitch1][v0_glitch2]blend=all_mode=screen:all_opacity=0.3[v0_glitched];"
            
            # Concatenate normal + glitched
            f"[v0_pre][v0_glitched]concat=n=2:v=1:a=0,settb=AVTB,fps=30[v0_final];"
            
            # === CLIP 2 PROCESSING ===
            # Normalize and split into 3 streams
            f"[1:v]settb=AVTB,fps=30[v1_base];"
            f"[v1_base]split=3[v1a][v1b][v1c];"
            
            # Glitched part - Layer 1: RGB shift (opposite direction)
            f"[v1a]trim=end={duration},setpts=PTS-STARTPTS,"
            f"geq=r='r(X+{rgb_shift},Y)':g='g(X,Y)':b='b(X-{rgb_shift},Y)'[v1_glitch1];"
            
            # Glitched part - Layer 2: Add noise + displacement
            f"[v1b]trim=end={duration},setpts=PTS-STARTPTS,"
            f"noise=c0s={int(noise_strength*100)}:allf=t,"
            f"geq=r='r(X-sin(Y/8)*4,Y)':g='g(X,Y)':b='b(X+sin(Y/8)*4,Y)'[v1_glitch2];"
            
            # Blend glitch layers
            f"[v1_glitch1][v1_glitch2]blend=all_mode=screen:all_opacity=0.3[v1_glitched];"
            
            # Normal part (after transition)
            f"[v1c]trim=start={duration},setpts=PTS-STARTPTS[v1_post];"
            
            # Concatenate glitched + normal
            f"[v1_glitched][v1_post]concat=n=2:v=1:a=0,settb=AVTB,fps=30[v1_final];"
            
            # === CROSSFADE ===
            f"[v0_final][v1_final]xfade=transition=fade:duration={duration}:offset={offset}[v]"
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
            logger.error(f"Dynamic glitch failed: {result.stderr[-1000:]}")
            raise RuntimeError("Dynamic glitch transition failed")
        
        logger.info("✓ Dynamic glitch applied successfully")
        return output_path
    
    @staticmethod
    def apply_flash_transition(
        clip1_path: str,
        clip2_path: str,
        output_path: str,
        duration: float = 0.3
    ) -> str:
        """White flash transition with normalized timebase"""
        logger.info("Applying flash transition")
        
        def get_duration(path):
            cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                   '-of', 'default=noprint_wrappers=1:nokey=1', path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return float(result.stdout.strip())
        
        clip1_dur = get_duration(clip1_path)
        offset = clip1_dur - duration
        
        # Normalize timebase and fps before xfade
        filter_complex = (
            f"[0:v]settb=AVTB,fps=30,fade=t=out:st={offset}:d={duration}:color=white[v0];"
            f"[1:v]settb=AVTB,fps=30,fade=t=in:st=0:d={duration}:color=white[v1];"
            f"[v0][v1]xfade=transition=fade:duration={duration}:offset={offset}[v]"
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
        Zoom punch - aggressive quick zoom at transition point
        Fixed version: applies zoom to END of clip1 only
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
        
        clip1_dur = get_duration(clip1_path)
        width, height = get_resolution(clip1_path)
        offset = clip1_dur - duration
        
        zoom_start = 1.0
        zoom_end = 4  # Aggressive zoom
        zoom_frames = int(duration * 30)
        
        # Split clip1 into before/during transition, apply zoom only to transition part
        filter_complex = (
            # Process clip1: normalize, split, apply zoom to last part
            f"[0:v]settb=AVTB,fps=30[v0_norm];"
            f"[v0_norm]split=2[v0_pre][v0_zoom];"
            
            # Normal part (no zoom)
            f"[v0_pre]trim=end={offset},setpts=PTS-STARTPTS[v0_before];"
            
            # Zoom part: scale up first, then zoom
            f"[v0_zoom]trim=start={offset},setpts=PTS-STARTPTS,"
            f"scale={int(width*2)}:{int(height*2)}:flags=lanczos,"
            f"zoompan="
            f"z='if(lte(on,{zoom_frames}),{zoom_start}+({zoom_end}-{zoom_start})*on/{zoom_frames},{zoom_end})':"
            f"x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':"
            f"d=1:"
            f"s={width}x{height}:"
            f"fps=30"
            f"[v0_after];"
            
            # Concatenate both parts
            f"[v0_before][v0_after]concat=n=2:v=1:a=0,settb=AVTB,fps=30[v0_final];"
            
            # Normalize clip2
            f"[1:v]settb=AVTB,fps=30[v1_final];"
            
            # Crossfade
            f"[v0_final][v1_final]xfade=transition=fade:duration={duration}:offset={offset}[v]"
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
        
        logger.info("✓ Zoom punch applied successfully")
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