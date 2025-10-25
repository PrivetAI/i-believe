"""
Video Service - FFmpeg-based rendering (no MoviePy)
"""
import gc
from pathlib import Path
from typing import List, Tuple
import sys
import random

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from models.slide import Slide
from utils.ffmpeg_renderer import FFmpegRenderer
from utils.frame_generator import FrameGenerator
from utils.ken_burns import generate_ken_burns_params, precalculate_trajectory
from utils.subtitle_renderer import prerender_words_batch, get_font
from utils import transitions
from utils.logger import get_logger
from pydub import AudioSegment

logger = get_logger(__name__)


class VideoService:
    """Service for video generation with FFmpeg"""
    
    def __init__(self, resolution: Tuple[int, int]):
        """
        Initialize video service
        
        Args:
            resolution: Video resolution (width, height)
        """
        self.resolution = resolution
        self.fps = config.DEFAULT_FPS
        
        logger.info(f"VideoService (FFmpeg): {resolution[0]}x{resolution[1]} @ {self.fps}fps")
    
    def merge_audio_files(self, audio_paths: List[str], output_path: str) -> str:
        """
        Merge multiple audio files into one
        
        Args:
            audio_paths: List of audio file paths
            output_path: Output merged audio path
            
        Returns:
            Path to merged audio
        """
        try:
            logger.info(f"Merging {len(audio_paths)} audio files")
            
            combined = AudioSegment.empty()
            
            for audio_path in audio_paths:
                if Path(audio_path).exists():
                    audio = AudioSegment.from_file(audio_path)
                    combined += audio
            
            combined.export(output_path, format="mp3")
            logger.info(f"✓ Audio merged: {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to merge audio: {e}")
            raise
    
    def assemble_video(
        self,
        slides: List[Slide],
        output_path: str,
        words_per_slide: List[List[dict]] = None
    ) -> str:
        """
        Assemble final video using FFmpeg pipeline
        
        Args:
            slides: List of Slide objects
            output_path: Output video path
            words_per_slide: Word timing data for each slide
            
        Returns:
            Path to generated video
        """
        logger.info(f"Assembling video: {len(slides)} slides")
        
        try:
            # Step 1: Merge all audio
            temp_audio_path = str(Path(output_path).with_suffix('.temp_audio.mp3'))
            audio_paths = [slide.audio_path for slide in slides if slide.audio_path]
            
            if audio_paths:
                self.merge_audio_files(audio_paths, temp_audio_path)
            else:
                temp_audio_path = None
            
            # Step 2: Prepare frame generator
            frame_gen = FrameGenerator(self.resolution, self.fps)
            
            # Step 3: Pre-calculate Ken Burns trajectories for all slides
            logger.info("Pre-calculating Ken Burns trajectories")
            kb_data = []
            
            for i, slide in enumerate(slides):
                kb_params = generate_ken_burns_params()
                kb_trajectory = precalculate_trajectory(
                    kb_params,
                    slide.duration,
                    self.fps
                )
                kb_data.append((kb_params, kb_trajectory))
                
                logger.debug(f"Slide {i+1}: {kb_params['direction']}")
            
            # Step 4: Pre-render all subtitle words
            logger.info("Pre-rendering subtitle words")
            font = get_font()
            
            all_words = []
            if words_per_slide:
                for words in words_per_slide:
                    all_words.extend(words)
            
            word_cache = prerender_words_batch(all_words, font) if all_words else {}
            
            # Step 5: Start FFmpeg renderer
            logger.info("Starting FFmpeg renderer")
            renderer = FFmpegRenderer(output_path, self.resolution, self.fps)
            renderer.start(audio_path=temp_audio_path)
            
            # Step 6: Generate and write frames
            current_time = 0.0
            transition_buffer = []  # Buffer for transition frames
            
            for slide_idx, slide in enumerate(slides):
                logger.info(f"Generating frames for slide {slide_idx + 1}/{len(slides)}")
                
                # Get data for this slide
                kb_params, kb_trajectory = kb_data[slide_idx]
                words_data = words_per_slide[slide_idx] if words_per_slide and slide_idx < len(words_per_slide) else []
                
                # Generate slide frames
                slide_frames = list(frame_gen.generate_slide_frames(
                    slide,
                    kb_params,
                    kb_trajectory,
                    words_data,
                    word_cache,
                    current_time
                ))
                
                # Write frames (except last transition_duration worth)
                transition_frame_count = int(config.TRANSITION_DURATION * self.fps)
                
                if slide_idx < len(slides) - 1:
                    # Not last slide - write all but transition frames
                    frames_to_write = slide_frames[:-transition_frame_count]
                    transition_buffer = slide_frames[-transition_frame_count:]
                else:
                    # Last slide - write all frames
                    frames_to_write = slide_frames
                
                # Write main frames
                for frame_idx, frame in enumerate(frames_to_write):
                    if not renderer.write_frame(frame):
                        raise RuntimeError(f"Failed to write frame {frame_idx} of slide {slide_idx + 1}")
                    
                    # Progress logging
                    if (frame_idx + 1) % 50 == 0:
                        logger.debug(f"Slide {slide_idx + 1}: written {frame_idx + 1}/{len(frames_to_write)} frames")
                
                # Apply transition if not last slide
                if slide_idx < len(slides) - 1:
                    logger.info(f"Applying transition after slide {slide_idx + 1}")
                    
                    # Get next slide preview frames
                    next_slide = slides[slide_idx + 1]
                    next_kb_params, next_kb_trajectory = kb_data[slide_idx + 1]
                    next_words_data = words_per_slide[slide_idx + 1] if words_per_slide and slide_idx + 1 < len(words_per_slide) else []
                    
                    # Generate preview frames for next slide
                    next_preview_frames = []
                    next_frame_gen = frame_gen.generate_slide_frames(
                        next_slide,
                        next_kb_params,
                        next_kb_trajectory,
                        next_words_data,
                        word_cache,
                        current_time + slide.duration
                    )
                    
                    for i, frame in enumerate(next_frame_gen):
                        next_preview_frames.append(frame)
                        if i >= transition_frame_count - 1:
                            break
                    
                    # Choose random transition
                    transition_type = transitions.get_random_transition()
                    logger.info(f"Transition type: {transition_type}")
                    
                    # Apply transition to outgoing frames
                    for i in range(len(transition_buffer)):
                        progress = i / max(len(transition_buffer) - 1, 1)
                        
                        if transition_type == "glitch":
                            frame = transitions.apply_glitch_frame(
                                transition_buffer[i], 
                                progress, 
                                i, 
                                self.fps,
                                fade_in=False
                            )
                        elif transition_type == "flash":
                            frame = transitions.apply_flash_frame(
                                transition_buffer[i], 
                                progress, 
                                fade_out=True
                            )
                        elif transition_type == "zoom_punch":
                            frame = transitions.apply_zoom_punch_frame(
                                transition_buffer[i], 
                                progress
                            )
                        else:
                            frame = transition_buffer[i]
                        
                        renderer.write_frame(frame)
                    
                    # Apply transition to incoming frames
                    for i in range(len(next_preview_frames)):
                        progress = i / max(len(next_preview_frames) - 1, 1)
                        
                        if transition_type == "glitch":
                            frame = transitions.apply_glitch_frame(
                                next_preview_frames[i], 
                                progress, 
                                i, 
                                self.fps,
                                fade_in=True
                            )
                        elif transition_type == "flash":
                            frame = transitions.apply_flash_frame(
                                next_preview_frames[i], 
                                1 - progress, 
                                fade_out=False
                            )
                        else:
                            frame = next_preview_frames[i]
                        
                        renderer.write_frame(frame)
                
                # Update time
                current_time += slide.duration
                
                # GC
                if config.GC_COLLECT_AFTER_SLIDE and (slide_idx + 1) % config.GC_COLLECT_INTERVAL == 0:
                    gc.collect()
                    logger.debug(f"GC collected after slide {slide_idx + 1}")
            
            # Step 7: Finalize video
            logger.info("Finalizing video")
            success = renderer.finish()
            
            if not success:
                raise RuntimeError("FFmpeg rendering failed")
            
            # Cleanup temp audio
            if temp_audio_path and Path(temp_audio_path).exists():
                Path(temp_audio_path).unlink()
            
            logger.info(f"✓ Video assembled successfully: {output_path}")
            
            # Final GC
            gc.collect()
            
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to assemble video: {e}", exc_info=True)
            raise