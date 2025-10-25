"""
Video transitions - Frame-based for FFmpeg pipeline
"""
import random
import numpy as np
from scipy.ndimage import zoom as scipy_zoom
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from utils.logger import get_logger

logger = get_logger(__name__)


def fast_resize_numpy(frame: np.ndarray, scale: float) -> np.ndarray:
    """Ultra-fast resize with scipy"""
    if abs(scale - 1.0) < 0.01:
        return frame
    return scipy_zoom(frame, (scale, scale, 1), order=1, prefilter=False)


def apply_glitch_frame(
    frame: np.ndarray, 
    progress: float, 
    frame_idx: int, 
    fps: float,
    fade_in: bool = False
) -> np.ndarray:
    """
    Apply glitch effect to single frame
    
    Args:
        frame: Input frame
        progress: Transition progress (0-1)
        frame_idx: Frame index
        fps: Frames per second
        fade_in: True for fade in, False for fade out
        
    Returns:
        Glitched frame
    """
    # 40% of frames get glitched
    if random.random() > 0.4:
        return frame
    
    result = frame.copy()
    
    if fade_in:
        # Horizontal slice shifts
        slice_height = frame.shape[0] // 8
        
        for i in range(0, frame.shape[0], slice_height * 2):
            offset = random.randint(-30, 30)
            end_slice = min(i + slice_height, frame.shape[0])
            
            if 0 < offset < frame.shape[1]:
                result[i:end_slice, offset:] = frame[i:end_slice, :-offset]
            elif -frame.shape[1] < offset < 0:
                result[i:end_slice, :offset] = frame[i:end_slice, -offset:]
    else:
        # RGB channel shift
        shift = int(30 * progress)
        
        if shift > 0:
            result[:, shift:, 0] = frame[:, :-shift, 0]  # Red
            result[:, :-shift, 2] = frame[:, shift:, 2]  # Blue
    
    return result


def apply_flash_frame(
    frame: np.ndarray, 
    progress: float,
    fade_out: bool = True
) -> np.ndarray:
    """
    Apply flash effect to single frame
    
    Args:
        frame: Input frame
        progress: Transition progress (0-1)
        fade_out: True for fade out, False for fade in
        
    Returns:
        Flashed frame
    """
    if fade_out:
        # Fade out: increase brightness
        brightness = int(progress * progress * 400)
        result = np.clip(frame.astype(np.int16) + brightness, 0, 255).astype(np.uint8)
        
        # Zoom at the end
        if progress > 0.6:
            zoom_factor = 1 + (progress - 0.6) * 1.0
            result = fast_resize_numpy(result, zoom_factor)
            
            # Crop to original size
            h, w = result.shape[:2]
            target_h, target_w = frame.shape[:2]
            start_y = (h - target_h) // 2
            start_x = (w - target_w) // 2
            result = result[start_y:start_y+target_h, start_x:start_x+target_w]
    else:
        # Fade in: decrease brightness
        brightness = int((1 - progress) * (1 - progress) * 400)
        result = np.clip(frame.astype(np.int16) + brightness, 0, 255).astype(np.uint8)
    
    return result


def apply_zoom_punch_frame(frame: np.ndarray, progress: float) -> np.ndarray:
    """
    Apply aggressive zoom punch to single frame
    
    Args:
        frame: Input frame
        progress: Transition progress (0-1)
        
    Returns:
        Zoomed frame
    """
    # Quadratic acceleration
    zoom_factor = 1.0 + (progress * progress * 3.0)
    
    # Fast zoom
    zoomed = fast_resize_numpy(frame, zoom_factor)
    
    # Crop to center
    h, w = zoomed.shape[:2]
    target_h, target_w = frame.shape[:2]
    
    start_y = max(0, (h - target_h) // 2)
    start_x = max(0, (w - target_w) // 2)
    
    end_y = min(h, start_y + target_h)
    end_x = min(w, start_x + target_w)
    
    cropped = zoomed[start_y:end_y, start_x:end_x]
    
    # Pad if needed
    if cropped.shape[0] < target_h or cropped.shape[1] < target_w:
        padded = np.zeros((target_h, target_w, 3), dtype=np.uint8)
        padded[:cropped.shape[0], :cropped.shape[1]] = cropped
        return padded
    
    return cropped


def get_random_transition() -> str:
    """Get random transition type"""
    return random.choice(config.TRANSITION_TYPES)