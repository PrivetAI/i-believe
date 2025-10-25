"""
Video Service - Pure FFmpeg with Ken Burns, Transitions, and Subtitles
No MoviePy - Maximum Performance
"""
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import List, Tuple
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from models.slide import Slide
from utils.logger import get_logger
from utils.effects import KenBurnsEffect, CustomTransitions, SubtitleEffect

logger = get_logger(__name__)


class VideoService:
    """Fast video generation with FFmpeg - Ken Burns + Transitions + Subtitles"""
    
    def __init__(self, resolution: Tuple[int, int]):
        self.resolution = resolution
        self.fps = config.DEFAULT_FPS
        logger.info(f"VideoService: {resolution[0]}x{resolution[1]} @ {self.fps}fps")
    
    def process_slide(
        self,
        slide: Slide,
        output_path: str,
        words: List[dict] = None
    ) -> str:
        """
        Process single slide: Ken Burns + Subtitles
        
        Args:
            slide: Slide object
            output_path: Output video path
            words: Word-level timestamps for subtitles
            
        Returns:
            Path to processed video
        """
        duration = max(slide.duration, config.MIN_SLIDE_DURATION)
        
        logger.debug(f"Processing slide: {Path(slide.image_path).name} ({duration:.2f}s)")
        
        # Create subtitle file first if needed
        srt_path = None
        if words:
            srt_path = str(output_path).replace('.mp4', '.srt')
            SubtitleEffect.create_srt_file(words, srt_path)
        
        # Build complete filter_complex as single chain
        filter_chain = []
        
        # Start with input
        filter_chain.append("[0:v]")
        
        # 1. Scale and pad
        filter_chain.append(
            f"scale={self.resolution[0]}:{self.resolution[1]}:"
            f"force_original_aspect_ratio=decrease,"
            f"pad={self.resolution[0]}:{self.resolution[1]}:"
            f"(ow-iw)/2:(oh-ih)/2:black"
        )
        
        # 2. Ken Burns effect (if enabled)
        if config.ENABLE_KEN_BURNS:
            kb_filter = KenBurnsEffect.build_filter(
                duration, 
                self.fps, 
                self.resolution
            )
            filter_chain.append(",")
            filter_chain.append(kb_filter)
        
        # 3. Set PTS
        filter_chain.append(",setpts=PTS-STARTPTS")
        
        # 4. Subtitles (if available)
        if srt_path:
            subtitle_filter = SubtitleEffect.build_subtitle_filter(srt_path)
            if subtitle_filter:
                filter_chain.append(",")
                filter_chain.append(subtitle_filter)
        
        # End with output label
        filter_chain.append("[out]")
        
        # Join everything into single filter string
        filter_complex = "".join(filter_chain)
        
        # Build FFmpeg command
        cmd = [
            'ffmpeg', '-y',
            '-loop', '1',
            '-t', str(duration),
            '-i', slide.image_path,
            '-i', slide.audio_path,
            '-filter_complex', filter_complex,
            '-map', '[out]',
            '-map', '1:a',
            '-c:v', 'libx264',
            '-preset', config.MOVIEPY_PRESET,
            '-crf', str(config.CRF),
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-shortest',
            '-r', str(self.fps),
            output_path
        ]
        
        # Execute FFmpeg
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=300
        )
        
        if result.returncode != 0:
            logger.error(f"FFmpeg stderr: {result.stderr[-1000:]}")
            raise RuntimeError(f"Failed to process slide: {result.returncode}")
        
        # Cleanup subtitle file
        if srt_path and Path(srt_path).exists():
            Path(srt_path).unlink()
        
        return output_path
    
    def apply_transition(
        self,
        clip1_path: str,
        clip2_path: str,
        output_path: str,
        transition_duration: float = None
    ) -> str:
        """
        Apply custom transition (glitch, flash, or zoom_punch)
        
        Args:
            clip1_path: First clip path
            clip2_path: Second clip path
            output_path: Output path
            transition_duration: Duration in seconds
            
        Returns:
            Path to output video with transition
        """
        if transition_duration is None:
            transition_duration = getattr(config, 'TRANSITION_DURATION', 0.3)
        
        # Get random transition from custom set
        transition = CustomTransitions.get_random_transition()
        
        logger.info(f"Applying '{transition}' transition")
        
        try:
            if transition == 'glitch':
                return CustomTransitions.apply_glitch_transition(
                    clip1_path, clip2_path, output_path, transition_duration
                )
            elif transition == 'flash':
                return CustomTransitions.apply_flash_transition(
                    clip1_path, clip2_path, output_path, transition_duration
                )
            elif transition == 'zoom_punch':
                return CustomTransitions.apply_zoom_punch_transition(
                    clip1_path, clip2_path, output_path, transition_duration
                )
            else:
                logger.warning(f"Unknown transition: {transition}, using fade")
                # Fallback to simple fade
                return self._apply_simple_fade(
                    clip1_path, clip2_path, output_path, transition_duration
                )
        except Exception as e:
            logger.error(f"Transition '{transition}' failed: {e}")
            raise
    
    def concatenate_videos(self, video_paths: List[str], output_path: str) -> str:
        """
        Concatenate videos without transitions (fallback)
        
        Args:
            video_paths: List of video file paths
            output_path: Output path
            
        Returns:
            Path to concatenated video
        """
        # Create concat file
        concat_file = str(output_path).replace('.mp4', '_concat.txt')
        
        with open(concat_file, 'w') as f:
            for path in video_paths:
                f.write(f"file '{Path(path).absolute()}'\n")
        
        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_file,
            '-c', 'copy',
            output_path
        ]
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=600
        )
        
        # Cleanup concat file
        Path(concat_file).unlink(missing_ok=True)
        
        if result.returncode != 0:
            logger.error(f"Concatenation error: {result.stderr[-1000:]}")
            raise RuntimeError(f"Failed to concatenate: {result.returncode}")
        
        return output_path
    
    def assemble_video(
        self,
        slides: List[Slide],
        output_path: str,
        words_per_slide: List[List[dict]] = None
    ) -> str:
        """
        Assemble video with Ken Burns + Transitions + Subtitles
        
        Process:
        1. Process each slide with Ken Burns and subtitles
        2. Apply transitions between slides
        3. Merge all clips into final video
        
        Args:
            slides: List of Slide objects
            output_path: Output video path
            words_per_slide: Word timestamps per slide for subtitles
            
        Returns:
            Path to final video
        """
        logger.info(f"Assembling video: {len(slides)} slides")
        
        try:
            if not slides:
                raise ValueError("No slides provided")
            
            # Validate inputs
            for i, slide in enumerate(slides):
                if not Path(slide.image_path).exists():
                    raise FileNotFoundError(f"Image not found: {slide.image_path}")
                if not Path(slide.audio_path).exists():
                    raise FileNotFoundError(f"Audio not found: {slide.audio_path}")
            
            # Create temp directory
            temp_dir = Path(output_path).parent / "temp_clips"
            temp_dir.mkdir(exist_ok=True)
            
            # Step 1: Process each slide with Ken Burns and subtitles
            logger.info("Step 1: Processing slides...")
            processed_clips = []
            
            for i, slide in enumerate(slides):
                logger.info(f"Processing slide {i+1}/{len(slides)}")
                
                temp_clip = temp_dir / f"slide_{i:03d}.mp4"
                words = words_per_slide[i] if words_per_slide and i < len(words_per_slide) else None
                
                self.process_slide(slide, str(temp_clip), words)
                processed_clips.append(str(temp_clip))
            
            # Step 2: Apply transitions between clips
            if len(processed_clips) > 1 and hasattr(config, 'TRANSITION_DURATION'):
                logger.info("Step 2: Applying transitions...")
                
                # Merge clips progressively with transitions
                current_clip = processed_clips[0]
                
                for i in range(1, len(processed_clips)):
                    logger.info(f"Transition {i}/{len(processed_clips)-1}")
                    
                    merged_clip = temp_dir / f"merged_{i:03d}.mp4"
                    
                    try:
                        self.apply_transition(
                            current_clip,
                            processed_clips[i],
                            str(merged_clip)
                        )
                        
                        # Remove previous merged clip to save space
                        if i > 1:
                            Path(current_clip).unlink(missing_ok=True)
                        
                        current_clip = str(merged_clip)
                        
                    except Exception as e:
                        logger.warning(f"Transition failed: {e}")
                        logger.info("Falling back to concatenation")
                        
                        # Fallback: concatenate without transitions
                        remaining_clips = [current_clip] + processed_clips[i:]
                        self.concatenate_videos(remaining_clips, output_path)
                        
                        # Cleanup and return
                        shutil.rmtree(temp_dir, ignore_errors=True)
                        return output_path
                
                # Move final merged clip to output
                shutil.move(current_clip, output_path)
                
            else:
                # Step 2 (no transitions): Simple concatenation
                logger.info("Step 2: Concatenating clips (no transitions)...")
                
                if len(processed_clips) == 1:
                    # Single clip - just move it
                    shutil.move(processed_clips[0], output_path)
                else:
                    # Multiple clips - concatenate
                    self.concatenate_videos(processed_clips, output_path)
            
            # Cleanup temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            # Verify output
            if not Path(output_path).exists():
                raise RuntimeError("Output file not created")
            
            file_size = Path(output_path).stat().st_size / (1024 * 1024)
            logger.info(f"✓ Video assembled: {file_size:.2f} MB")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to assemble video: {e}", exc_info=True)
            
            # Cleanup on error
            if 'temp_dir' in locals():
                shutil.rmtree(temp_dir, ignore_errors=True)
            
            raise