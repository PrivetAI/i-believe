"""
Ken Burns effect implementation - Enhanced for visibility
"""
import sys
from pathlib import Path
import random
from typing import Dict
import numpy as np

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from utils.logger import get_logger

logger = get_logger(__name__)


def generate_ken_burns_params() -> Dict:
    """
    Generate random Ken Burns effect parameters
    
    Returns:
        Dictionary with 'direction', 'zoom_start', 'zoom_end', 'pan_x', 'pan_y'
    """
    direction = random.choice(config.KEN_BURNS_DIRECTIONS)
    
    # More dramatic zoom range
    zoom_start = random.uniform(1.0, 1.2)
    zoom_end = random.uniform(1.3, 1.5)
    
    # Ensure zoom in/out is more noticeable
    if direction == "zoom_out":
        zoom_start, zoom_end = zoom_end, zoom_start
    
    # More dramatic pan
    pan_x = random.uniform(0.1, 0.2)
    pan_y = random.uniform(0.1, 0.2)
    
    params = {
        'direction': direction,
        'zoom_start': zoom_start,
        'zoom_end': zoom_end,
        'pan_x': pan_x,
        'pan_y': pan_y
    }
    
    logger.info(f"Generated Ken Burns params: {params}")
    return params


def apply_ken_burns(clip, params: Dict, duration: float):
    """
    Apply Ken Burns effect to a clip with enhanced visibility
    
    Args:
        clip: MoviePy VideoClip or ImageClip
        params: Ken Burns parameters from generate_ken_burns_params()
        duration: Effect duration in seconds
        
    Returns:
        Transformed clip with Ken Burns effect
    """
    direction = params['direction']
    zoom_start = params['zoom_start']
    zoom_end = params['zoom_end']
    pan_x = params['pan_x']
    pan_y = params['pan_y']
    
    w, h = clip.size
    
    logger.info(f"Applying Ken Burns effect: {direction}")
    logger.info(f"Zoom: {zoom_start:.2f} -> {zoom_end:.2f}")
    logger.debug(f"Clip size: {w}x{h}, Duration: {duration}s")
    
    def effect(get_frame, t):
        progress = t / duration if duration > 0 else 0
        frame = get_frame(t)
        
        # Calculate current zoom
        zoom = zoom_start + (zoom_end - zoom_start) * progress
        
        # Resize frame
        from PIL import Image
        img = Image.fromarray(frame)
        new_w = int(w * zoom)
        new_h = int(h * zoom)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        zoomed = np.array(img)
        
        # Calculate pan offset
        x_offset = 0
        y_offset = 0
        
        if direction == "pan_left":
            max_offset = zoomed.shape[1] - w
            x_offset = int(max_offset * pan_x * progress)
        elif direction == "pan_right":
            max_offset = zoomed.shape[1] - w
            x_offset = int(max_offset * (1 - pan_x * progress))
        elif direction == "pan_up":
            max_offset = zoomed.shape[0] - h
            y_offset = int(max_offset * pan_y * progress)
        elif direction == "pan_down":
            max_offset = zoomed.shape[0] - h
            y_offset = int(max_offset * (1 - pan_y * progress))
        else:
            # Center crop for zoom only
            x_offset = (zoomed.shape[1] - w) // 2
            y_offset = (zoomed.shape[0] - h) // 2
        
        # Ensure offsets are within bounds
        x_offset = max(0, min(x_offset, zoomed.shape[1] - w))
        y_offset = max(0, min(y_offset, zoomed.shape[0] - h))
        
        # Crop to original size
        result = zoomed[y_offset:y_offset+h, x_offset:x_offset+w]
        
        return result
    
    logger.info(f"Applied pan: {direction}")
    return clip.fl(effect)