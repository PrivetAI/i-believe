"""
Ken Burns effect implementation - Enhanced for visibility
"""
import sys
from pathlib import Path
import random
from typing import Dict, Tuple

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
        
        # Calculate zoom
        if 'zoom' in direction or direction.startswith('pan'):
            if direction == "zoom_out":
                zoom = zoom_start - (zoom_start - zoom_end) * progress
            else:
                zoom = zoom_start + (zoom_end - zoom_start) * progress
            
            new_w = int(w * zoom)
            new_h = int(h * zoom)
            
            from PIL import Image
            img = Image.fromarray(frame)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            frame = np.array(img)
        
        # Calculate pan offset
        x_offset = 0
        y_offset = 0
        
        if direction == "pan_left":
            x_offset = -int(frame.shape[1] * pan_x * progress)
        elif direction == "pan_right":
            x_offset = int(frame.shape[1] * pan_x * progress)
        elif direction == "pan_up":
            y_offset = -int(frame.shape[0] * pan_y * progress)
        elif direction == "pan_down":
            y_offset = int(frame.shape[0] * pan_y * progress)
        
        # Crop/pad to original size
        fh, fw = frame.shape[:2]
        result = np.zeros((h, w, 3), dtype=np.uint8)
        
        src_x = max(0, x_offset)
        src_y = max(0, y_offset)
        dst_x = max(0, -x_offset)
        dst_y = max(0, -y_offset)
        
        copy_w = min(w - dst_x, fw - src_x)
        copy_h = min(h - dst_y, fh - src_y)
        
        if copy_w > 0 and copy_h > 0:
            result[dst_y:dst_y+copy_h, dst_x:dst_x+copy_w] = frame[src_y:src_y+copy_h, src_x:src_x+copy_w]
        
        return result
    
    from moviepy.editor import VideoClip
    import numpy as np
    
    logger.info(f"Applied effect: {direction}")
    return clip.fl(effect)