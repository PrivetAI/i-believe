"""
Ken Burns effect implementation - Optimized for low-end CPU
"""
import sys
from pathlib import Path
import random
from typing import Dict
import numpy as np
from scipy.ndimage import zoom as scipy_zoom

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from utils.logger import get_logger

logger = get_logger(__name__)


def generate_ken_burns_params() -> Dict:
    """Generate Ken Burns parameters from config ranges"""
    direction = random.choice(config.KEN_BURNS_DIRECTIONS)
    
    zoom_start = random.uniform(*config.KEN_BURNS_ZOOM_RANGE)
    zoom_end = random.uniform(*config.KEN_BURNS_ZOOM_RANGE)
    
    if abs(zoom_end - zoom_start) < 0.1:
        zoom_end = zoom_start + 0.2
    
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
    
    logger.info(f"Ken Burns params: {params}")
    return params


def resize_frame_numpy(frame: np.ndarray, scale: float) -> np.ndarray:
    """
    Fast frame resize using NumPy/SciPy (faster than PIL for video frames)
    
    Args:
        frame: Input frame array
        scale: Scale factor
        
    Returns:
        Resized frame
    """
    if abs(scale - 1.0) < 0.01:
        return frame
    
    # Use scipy zoom which is faster than PIL for this use case
    # zoom works on each dimension: (height, width, channels)
    return scipy_zoom(frame, (scale, scale, 1), order=1, prefilter=False)


def apply_ken_burns(clip, params: Dict, duration: float):
    """
    Apply Ken Burns effect - Optimized with NumPy operations
    No PIL conversion, pure NumPy for speed
    """
    direction = params['direction']
    zoom_start = params['zoom_start']
    zoom_end = params['zoom_end']
    pan_x = params['pan_x']
    pan_y = params['pan_y']
    
    w, h = clip.size
    
    logger.info(f"Applying Ken Burns (optimized): {direction}, zoom {zoom_start:.2f}->{zoom_end:.2f}")
    
    # Pre-calculate constants
    zoom_diff = zoom_end - zoom_start
    
    # Determine pan factors
    pan_x_factor = 0
    pan_y_factor = 0
    
    if direction == "pan_left":
        pan_x_factor = pan_x
    elif direction == "pan_right":
        pan_x_factor = -pan_x
    elif direction == "pan_up":
        pan_y_factor = pan_y
    elif direction == "pan_down":
        pan_y_factor = -pan_y
    
    def effect(get_frame, t):
        progress = min(t / duration, 1.0) if duration > 0 else 0
        frame = get_frame(t)
        
        # Calculate zoom
        zoom = zoom_start + zoom_diff * progress
        
        # Fast resize with NumPy/SciPy
        zoomed = resize_frame_numpy(frame, zoom)
        
        zoomed_h, zoomed_w = zoomed.shape[:2]
        
        # Calculate offsets
        if direction in ["pan_left", "pan_right"]:
            max_x = max(0, zoomed_w - w)
            x_offset = int(max_x * (0.5 + pan_x_factor * progress))
            y_offset = (zoomed_h - h) // 2
        elif direction in ["pan_up", "pan_down"]:
            x_offset = (zoomed_w - w) // 2
            max_y = max(0, zoomed_h - h)
            y_offset = int(max_y * (0.5 + pan_y_factor * progress))
        else:
            x_offset = (zoomed_w - w) // 2
            y_offset = (zoomed_h - h) // 2
        
        # Clamp offsets
        x_offset = max(0, min(x_offset, zoomed_w - w))
        y_offset = max(0, min(y_offset, zoomed_h - h))
        
        # Crop using NumPy slicing (very fast)
        return zoomed[y_offset:y_offset+h, x_offset:x_offset+w]
    
    return clip.fl(effect)