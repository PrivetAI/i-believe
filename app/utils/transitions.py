"""
Video transitions - Optimized for speed without losing effects
"""
import sys
from pathlib import Path
import random
from typing import List
import numpy as np
from moviepy.editor import VideoClip, concatenate_videoclips
from scipy.ndimage import zoom as scipy_zoom, rotate

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from utils.logger import get_logger

logger = get_logger(__name__)


def fast_resize_numpy(frame: np.ndarray, scale: float) -> np.ndarray:
    """Ultra-fast resize with scipy"""
    if abs(scale - 1.0) < 0.01:
        return frame
    return scipy_zoom(frame, (scale, scale, 1), order=1, prefilter=False)


def apply_glitch_transition(clip1: VideoClip, clip2: VideoClip, duration: float) -> List[VideoClip]:
    """
    Optimized glitch transition - fewer random calls
    """
    total1 = clip1.duration
    
    # Pre-calculate glitch pattern
    glitch_frames = set(np.random.choice(
        range(int((total1 - duration) * 24), int(total1 * 24)),
        size=int(duration * 24 * 0.4),  # 40% of frames glitch
        replace=False
    ))
    
    def glitch_out(get_frame, t):
        if t >= total1 - duration:
            frame_idx = int(t * 24)
            
            if frame_idx in glitch_frames:
                frame = get_frame(t)
                progress = (t - (total1 - duration)) / duration
                shift = int(30 * progress)
                
                if shift > 0:
                    frame_shifted = frame.copy()
                    frame_shifted[:, shift:, 0] = frame[:, :-shift, 0]
                    frame_shifted[:, :-shift, 2] = frame[:, shift:, 2]
                    return frame_shifted
            
            return get_frame(t)
        return get_frame(t)
    
    def glitch_in(get_frame, t):
        if t < duration:
            frame_idx = int(t * 24)
            
            if frame_idx in glitch_frames:
                frame = get_frame(t)
                slice_height = frame.shape[0] // 8
                
                for i in range(0, frame.shape[0], slice_height * 2):
                    offset = random.randint(-30, 30)
                    end_slice = min(i + slice_height, frame.shape[0])
                    
                    if 0 < offset < frame.shape[1]:
                        frame[i:end_slice, offset:] = frame[i:end_slice, :-offset]
                    elif -frame.shape[1] < offset < 0:
                        frame[i:end_slice, :offset] = frame[i:end_slice, -offset:]
                
                return frame
            
            return get_frame(t)
        return get_frame(t)
    
    clip1_glitched = clip1.fl(glitch_out)
    clip2_glitched = clip2.fl(glitch_in)
    
    return [clip1_glitched, clip2_glitched]


def apply_flash_transition(clip1: VideoClip, clip2: VideoClip, duration: float) -> List[VideoClip]:
    """
    Optimized flash transition - vectorized operations
    """
    total1 = clip1.duration
    
    def flash_out(get_frame, t):
        if t >= total1 - duration:
            progress = (t - (total1 - duration)) / duration
            frame = get_frame(t)
            
            # Vectorized brightness calculation
            brightness = int(progress * progress * 400)
            flash_frame = np.clip(frame.astype(np.int16) + brightness, 0, 255).astype(np.uint8)
            
            # Zoom effect
            if progress > 0.6:
                zoom_factor = 1 + (progress - 0.6) * 1.0
                flash_frame = fast_resize_numpy(flash_frame, zoom_factor)
                h, w = flash_frame.shape[:2]
                target_h, target_w = frame.shape[:2]
                start_y = (h - target_h) // 2
                start_x = (w - target_w) // 2
                flash_frame = flash_frame[start_y:start_y+target_h, start_x:start_x+target_w]
            
            return flash_frame
        return get_frame(t)
    
    def flash_in(get_frame, t):
        if t < duration:
            progress = t / duration
            frame = get_frame(t)
            
            brightness = int((1 - progress) * (1 - progress) * 400)
            flash_frame = np.clip(frame.astype(np.int16) + brightness, 0, 255).astype(np.uint8)
            
            return flash_frame
        return get_frame(t)
    
    clip1_flash = clip1.fl(flash_out)
    clip2_flash = clip2.fl(flash_in)
    
    return [clip1_flash, clip2_flash]


def apply_zoom_punch_transition(clip1: VideoClip, clip2: VideoClip, duration: float) -> List[VideoClip]:
    """
    Optimized aggressive zoom transition
    """
    total1 = clip1.duration
    
    def aggressive_zoom_in(get_frame, t):
        if t >= total1 - duration:
            progress = (t - (total1 - duration)) / duration
            frame = get_frame(t)
            
            # Quadratic zoom acceleration
            zoom_factor = 1.0 + (progress * progress * 3.0)
            
            zoomed = fast_resize_numpy(frame, zoom_factor)
            
            # Fast crop to center
            h, w = zoomed.shape[:2]
            target_h, target_w = frame.shape[:2]
            
            start_y = max(0, (h - target_h) // 2)
            start_x = max(0, (w - target_w) // 2)
            
            end_y = min(h, start_y + target_h)
            end_x = min(w, start_x + target_w)
            
            cropped = zoomed[start_y:end_y, start_x:end_x]
            
            if cropped.shape[0] < target_h or cropped.shape[1] < target_w:
                padded = np.zeros((target_h, target_w, 3), dtype=np.uint8)
                padded[:cropped.shape[0], :cropped.shape[1]] = cropped
                return padded
            
            return cropped
        return get_frame(t)
    
    clip1_zoom = clip1.fl(aggressive_zoom_in)
    
    return [clip1_zoom, clip2]


def apply_transitions(clips: List[VideoClip]) -> VideoClip:
    """
    Apply random transitions - optimized selection
    """
    if len(clips) <= 1:
        logger.info("Single clip, no transitions")
        return clips[0] if clips else None
    
    logger.info(f"Applying transitions: {len(clips)} clips")
    
    # Pre-define all transitions
    transition_functions = [
        ("glitch", apply_glitch_transition),
        ("flash", apply_flash_transition),
        ("zoom_punch", apply_zoom_punch_transition)
    ]
    
    result_clips = []
    
    for i in range(len(clips)):
        clip = clips[i]
        
        if i > 0:
            # Random transition
            transition_name, transition_func = random.choice(transition_functions)
            logger.info(f"Transition {i}: {transition_name}")
            
            prev_clip, curr_clip = transition_func(
                result_clips[-1],
                clip,
                config.TRANSITION_DURATION
            )
            
            result_clips[-1] = prev_clip
            clip = curr_clip
        
        result_clips.append(clip)
    
    logger.info("Concatenating clips")
    final_clip = concatenate_videoclips(result_clips, method="compose")
    
    logger.info("✓ Transitions applied")
    return final_clip