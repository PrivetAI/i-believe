"""
Video transition effects - Fast and Dynamic
"""
import sys
from pathlib import Path
import random
from typing import List
import numpy as np
from moviepy.editor import VideoClip, concatenate_videoclips

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from utils.logger import get_logger

logger = get_logger(__name__)


def apply_glitch_transition(clip1: VideoClip, clip2: VideoClip, duration: float) -> List[VideoClip]:
    """Apply glitch transition effect"""
    def glitch_effect(get_frame, t):
        if t < duration:
            frame = get_frame(t)
            progress = t / duration
            
            # Random glitch intensity
            if random.random() < 0.3:  # 30% chance per frame
                # RGB channel shift
                shift = int(20 * (1 - progress))
                if shift > 0:
                    frame_shifted = frame.copy()
                    frame_shifted[:, shift:, 0] = frame[:, :-shift, 0]  # Red shift
                    frame_shifted[:, :-shift, 2] = frame[:, shift:, 2]  # Blue shift
                    return frame_shifted
            
            return frame
        return get_frame(t)
    
    # Apply glitch to end of clip1
    clip1_glitched = clip1.fl(glitch_effect)
    
    # Quick cut to clip2 with glitch
    def glitch_in_effect(get_frame, t):
        if t < duration:
            frame = get_frame(t)
            if random.random() < 0.4:
                # Horizontal slicing
                slice_height = frame.shape[0] // 10
                for i in range(0, frame.shape[0], slice_height * 2):
                    offset = random.randint(-30, 30)
                    if offset > 0:
                        frame[i:i+slice_height, offset:] = frame[i:i+slice_height, :-offset]
                    elif offset < 0:
                        frame[i:i+slice_height, :offset] = frame[i:i+slice_height, -offset:]
            return frame
        return get_frame(t)
    
    clip2_glitched = clip2.fl(glitch_in_effect)
    
    return [clip1_glitched, clip2_glitched]


def apply_spin_blur_transition(clip1: VideoClip, clip2: VideoClip, duration: float) -> List[VideoClip]:
    """Apply fast spin blur transition"""
    from PIL import Image
    
    def spin_blur_out(get_frame, t):
        total = clip1.duration
        if t > total - duration:
            progress = (t - (total - duration)) / duration
            frame = get_frame(t)
            
            # Convert to PIL for rotation
            img = Image.fromarray(frame)
            
            # Fast spin with increasing blur
            angle = progress * 180  # Half rotation
            blur_amount = int(progress * 15)
            
            # Rotate
            img_rotated = img.rotate(angle, resample=Image.BILINEAR)
            
            # Simple blur simulation by downsampling and upsampling
            if blur_amount > 0:
                w, h = img_rotated.size
                scale = max(1, blur_amount)
                img_small = img_rotated.resize((w//scale, h//scale), Image.BILINEAR)
                img_rotated = img_small.resize((w, h), Image.BILINEAR)
            
            return np.array(img_rotated)
        return get_frame(t)
    
    def spin_blur_in(get_frame, t):
        if t < duration:
            progress = t / duration
            frame = get_frame(t)
            
            img = Image.fromarray(frame)
            
            # Fast spin from rotated state
            angle = (1 - progress) * 180
            blur_amount = int((1 - progress) * 15)
            
            img_rotated = img.rotate(angle, resample=Image.BILINEAR)
            
            if blur_amount > 0:
                w, h = img_rotated.size
                scale = max(1, blur_amount)
                img_small = img_rotated.resize((w//scale, h//scale), Image.BILINEAR)
                img_rotated = img_small.resize((w, h), Image.BILINEAR)
            
            return np.array(img_rotated)
        return get_frame(t)
    
    clip1_spin = clip1.fl(spin_blur_out)
    clip2_spin = clip2.fl(spin_blur_in)
    
    return [clip1_spin, clip2_spin]


def apply_flash_transition(clip1: VideoClip, clip2: VideoClip, duration: float) -> List[VideoClip]:
    """Apply flash/explosion transition"""
    def flash_out(get_frame, t):
        total = clip1.duration
        if t > total - duration:
            progress = (t - (total - duration)) / duration
            frame = get_frame(t)
            
            # Bright flash with expansion
            brightness = int(progress * 255)
            flash_frame = np.clip(frame.astype(float) + brightness, 0, 255).astype(np.uint8)
            
            # Add radial expansion effect
            if progress > 0.5:
                zoom = 1 + (progress - 0.5) * 0.4  # Slight zoom out
                from PIL import Image
                img = Image.fromarray(flash_frame)
                w, h = img.size
                new_w, new_h = int(w * zoom), int(h * zoom)
                img_zoomed = img.resize((new_w, new_h), Image.BILINEAR)
                
                # Crop center
                left = (new_w - w) // 2
                top = (new_h - h) // 2
                flash_frame = np.array(img_zoomed.crop((left, top, left + w, top + h)))
            
            return flash_frame
        return get_frame(t)
    
    def flash_in(get_frame, t):
        if t < duration:
            progress = t / duration
            frame = get_frame(t)
            
            # Fade from white
            brightness = int((1 - progress) * 255)
            flash_frame = np.clip(frame.astype(float) + brightness, 0, 255).astype(np.uint8)
            
            # Zoom in from expanded state
            if progress < 0.5:
                zoom = 1.2 - progress * 0.4
                from PIL import Image
                img = Image.fromarray(flash_frame)
                w, h = img.size
                new_w, new_h = int(w * zoom), int(h * zoom)
                img_zoomed = img.resize((new_w, new_h), Image.BILINEAR)
                
                left = (new_w - w) // 2
                top = (new_h - h) // 2
                flash_frame = np.array(img_zoomed.crop((left, top, left + w, top + h)))
            
            return flash_frame
        return get_frame(t)
    
    clip1_flash = clip1.fl(flash_out)
    clip2_flash = clip2.fl(flash_in)
    
    return [clip1_flash, clip2_flash]


def apply_zoom_punch_transition(clip1: VideoClip, clip2: VideoClip, duration: float) -> List[VideoClip]:
    """Apply fast zoom-in punch transition"""
    from PIL import Image
    
    def zoom_out_punch(get_frame, t):
        total = clip1.duration
        if t > total - duration:
            progress = (t - (total - duration)) / duration
            frame = get_frame(t)
            
            # Fast zoom in (punch forward)
            zoom = 1 + progress * 0.5  # Zoom to 1.5x
            
            img = Image.fromarray(frame)
            w, h = img.size
            new_w, new_h = int(w * zoom), int(h * zoom)
            img_zoomed = img.resize((new_w, new_h), Image.BILINEAR)
            
            # Crop center
            left = (new_w - w) // 2
            top = (new_h - h) // 2
            result = np.array(img_zoomed.crop((left, top, left + w, top + h)))
            
            return result
        return get_frame(t)
    
    def zoom_in_punch(get_frame, t):
        if t < duration:
            progress = t / duration
            frame = get_frame(t)
            
            # Start zoomed out, punch in quickly
            zoom = 1.5 - progress * 0.5  # From 1.5x to 1x
            
            img = Image.fromarray(frame)
            w, h = img.size
            new_w, new_h = int(w * zoom), int(h * zoom)
            img_zoomed = img.resize((new_w, new_h), Image.BILINEAR)
            
            left = (new_w - w) // 2
            top = (new_h - h) // 2
            result = np.array(img_zoomed.crop((left, top, left + w, top + h)))
            
            return result
        return get_frame(t)
    
    clip1_punch = clip1.fl(zoom_out_punch)
    clip2_punch = clip2.fl(zoom_in_punch)
    
    return [clip1_punch, clip2_punch]


def apply_transitions(clips: List[VideoClip]) -> VideoClip:
    """
    Apply fast dynamic transitions between clips
    Transitions: Glitch, Spin Blur, Flash/Explosion, Zoom Punch
    
    Args:
        clips: List of video clips
        
    Returns:
        Single video clip with transitions applied
    """
    if len(clips) <= 1:
        logger.info("Only one clip, no transitions needed")
        return clips[0] if clips else None
    
    logger.info(f"Applying fast transitions between {len(clips)} clips")
    
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
            # Choose random transition
            transition_name, transition_func = random.choice(transition_functions)
            logger.info(f"Transition {i}: {transition_name}")
            
            # Apply transition (modifies both previous and current clip)
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
    final_clip = concatenate_videoclips(result_clips, method="compose")
    
    logger.info("Fast transitions applied successfully")
    return final_clip