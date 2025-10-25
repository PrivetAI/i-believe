"""
Video transition effects - Optimized and Fixed
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
    """Fast resize using scipy"""
    if abs(scale - 1.0) < 0.01:
        return frame
    return scipy_zoom(frame, (scale, scale, 1), order=1, prefilter=False)


def apply_glitch_transition(clip1: VideoClip, clip2: VideoClip, duration: float) -> List[VideoClip]:
    """Apply glitch transition - RGB channel shift and slicing"""
    total1 = clip1.duration
    
    def glitch_out(get_frame, t):
        if t >= total1 - duration:
            frame = get_frame(t)
            progress = (t - (total1 - duration)) / duration
            
            # More aggressive glitch near end
            if random.random() < (0.3 + progress * 0.5):
                shift = int(30 * progress)
                if shift > 0:
                    frame_shifted = frame.copy()
                    # RGB channel separation
                    frame_shifted[:, shift:, 0] = frame[:, :-shift, 0]  # Red
                    frame_shifted[:, :-shift, 2] = frame[:, shift:, 2]  # Blue
                    return frame_shifted
            return frame
        return get_frame(t)
    
    def glitch_in(get_frame, t):
        if t < duration:
            frame = get_frame(t)
            progress = t / duration
            
            # Horizontal slicing glitch
            if random.random() < (0.5 - progress * 0.4):
                slice_height = max(10, frame.shape[0] // 8)
                for i in range(0, frame.shape[0], slice_height * 2):
                    offset = random.randint(-40, 40)
                    end_slice = min(i + slice_height, frame.shape[0])
                    if offset > 0 and offset < frame.shape[1]:
                        frame[i:end_slice, offset:] = frame[i:end_slice, :-offset]
                    elif offset < 0 and -offset < frame.shape[1]:
                        frame[i:end_slice, :offset] = frame[i:end_slice, -offset:]
            return frame
        return get_frame(t)
    
    clip1_glitched = clip1.fl(glitch_out)
    clip2_glitched = clip2.fl(glitch_in)
    
    return [clip1_glitched, clip2_glitched]


def apply_spin_blur_transition(clip1: VideoClip, clip2: VideoClip, duration: float) -> List[VideoClip]:
    """Apply fast spin with motion blur"""
    total1 = clip1.duration
    
    def spin_out(get_frame, t):
        if t >= total1 - duration:
            progress = (t - (total1 - duration)) / duration
            frame = get_frame(t)
            
            # Fast aggressive spin
            angle = progress * 360  # Full rotation
            frame_rotated = rotate(frame, angle, reshape=False, order=1, prefilter=False)
            
            # Motion blur effect
            blur_factor = int(progress * 8) + 1
            if blur_factor > 1:
                h, w = frame_rotated.shape[:2]
                small = fast_resize_numpy(frame_rotated, 1.0 / blur_factor)
                frame_rotated = fast_resize_numpy(small, blur_factor)
            
            return frame_rotated
        return get_frame(t)
    
    def spin_in(get_frame, t):
        if t < duration:
            progress = t / duration
            frame = get_frame(t)
            
            # Spin from rotated
            angle = (1 - progress) * 360
            frame_rotated = rotate(frame, angle, reshape=False, order=1, prefilter=False)
            
            blur_factor = int((1 - progress) * 8) + 1
            if blur_factor > 1:
                h, w = frame_rotated.shape[:2]
                small = fast_resize_numpy(frame_rotated, 1.0 / blur_factor)
                frame_rotated = fast_resize_numpy(small, blur_factor)
            
            return frame_rotated
        return get_frame(t)
    
    clip1_spin = clip1.fl(spin_out)
    clip2_spin = clip2.fl(spin_in)
    
    return [clip1_spin, clip2_spin]


def apply_flash_transition(clip1: VideoClip, clip2: VideoClip, duration: float) -> List[VideoClip]:
    """Apply bright flash explosion transition"""
    total1 = clip1.duration
    
    def flash_out(get_frame, t):
        if t >= total1 - duration:
            progress = (t - (total1 - duration)) / duration
            frame = get_frame(t)
            
            # Aggressive brightness increase
            brightness = int(progress * progress * 400)  # Quadratic for punch
            flash_frame = np.clip(frame.astype(np.int16) + brightness, 0, 255).astype(np.uint8)
            
            # Slight zoom for explosion effect
            if progress > 0.6:
                zoom_factor = 1 + (progress - 0.6) * 1.0  # Up to 1.4x
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
            
            # Fade from white
            brightness = int((1 - progress) * (1 - progress) * 400)
            flash_frame = np.clip(frame.astype(np.int16) + brightness, 0, 255).astype(np.uint8)
            
            return flash_frame
        return get_frame(t)
    
    clip1_flash = clip1.fl(flash_out)
    clip2_flash = clip2.fl(flash_in)
    
    return [clip1_flash, clip2_flash]


def apply_zoom_punch_transition(clip1: VideoClip, clip2: VideoClip, duration: float) -> List[VideoClip]:
    """
    Apply AGGRESSIVE zoom in transition - zooms into infinity then instant cut
    Clip1: zooms IN aggressively (1.0x -> 4.0x+)
    Clip2: starts normally (instant cut, no zoom)
    """
    total1 = clip1.duration
    
    def aggressive_zoom_in(get_frame, t):
        if t >= total1 - duration:
            progress = (t - (total1 - duration)) / duration
            frame = get_frame(t)
            
            # AGGRESSIVE zoom: 1.0 -> 4.0x (quadratic easing for acceleration)
            zoom_factor = 1.0 + (progress * progress * 3.0)
            
            zoomed = fast_resize_numpy(frame, zoom_factor)
            
            # Crop center to original size
            h, w = zoomed.shape[:2]
            target_h, target_w = frame.shape[:2]
            
            start_y = max(0, (h - target_h) // 2)
            start_x = max(0, (w - target_w) // 2)
            
            end_y = min(h, start_y + target_h)
            end_x = min(w, start_x + target_w)
            
            cropped = zoomed[start_y:end_y, start_x:end_x]
            
            # If cropped is smaller than target (edge case), pad it
            if cropped.shape[0] < target_h or cropped.shape[1] < target_w:
                padded = np.zeros((target_h, target_w, 3), dtype=np.uint8)
                padded[:cropped.shape[0], :cropped.shape[1]] = cropped
                return padded
            
            return cropped
        return get_frame(t)
    
    # Clip2 starts normally - NO zoom effect, instant cut
    clip1_zoom = clip1.fl(aggressive_zoom_in)
    
    return [clip1_zoom, clip2]


def apply_transitions(clips: List[VideoClip]) -> VideoClip:
    """
    Apply random transitions between clips
    FIXED: Proper random selection with logging
    """
    if len(clips) <= 1:
        logger.info("Only one clip, no transitions needed")
        return clips[0] if clips else None
    
    logger.info(f"Applying transitions between {len(clips)} clips")
    
    # All available transition functions
    transition_functions = [
        ("glitch", apply_glitch_transition),
        ("spin_blur", apply_spin_blur_transition),
        ("flash", apply_flash_transition),
        ("zoom_punch", apply_zoom_punch_transition)
    ]
    
    result_clips = []
    
    for i in range(len(clips)):
        clip = clips[i]
        
        if i > 0:
            # Random selection with seed reset to ensure true randomness
            transition_name, transition_func = random.choice(transition_functions)
            logger.info(f"Applying transition {i}/{len(clips)-1}: {transition_name}")
            
            # Apply transition
            prev_clip, curr_clip = transition_func(
                result_clips[-1],
                clip,
                config.TRANSITION_DURATION
            )
            
            # Replace previous clip with transitioned version
            result_clips[-1] = prev_clip
            clip = curr_clip
        
        result_clips.append(clip)
    
    # Concatenate all clips
    logger.info("Concatenating clips with transitions")
    final_clip = concatenate_videoclips(result_clips, method="compose")
    
    logger.info("Transitions applied successfully")
    return final_clip