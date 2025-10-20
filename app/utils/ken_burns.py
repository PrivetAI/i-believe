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
    from moviepy.editor import VideoClip
    
    direction = params['direction']
    zoom_start = params['zoom_start']
    zoom_end = params['zoom_end']
    pan_x = params['pan_x']
    pan_y = params['pan_y']
    
    w, h = clip.size
    
    logger.info(f"Applying Ken Burns effect: {direction}")
    logger.info(f"Zoom: {zoom_start:.2f} -> {zoom_end:.2f}")
    logger.debug(f"Clip size: {w}x{h}, Duration: {duration}s")
    
    # Apply zoom effect
    if 'zoom' in direction:
        if direction == "zoom_in":
            def resize_func(t):
                progress = t / duration if duration > 0 else 0
                zoom = zoom_start + (zoom_end - zoom_start) * progress
                return zoom
        else:  # zoom_out
            def resize_func(t):
                progress = t / duration if duration > 0 else 0
                zoom = zoom_start - (zoom_start - zoom_end) * progress
                return zoom
        
        clip = clip.resize(resize_func)
        logger.info(f"Applied zoom from {zoom_start:.2f}x to {zoom_end:.2f}x")
    
    # Apply pan effect
    if 'pan' in direction:
        if direction == "pan_left":
            def pos_func(t):
                progress = t / duration if duration > 0 else 0
                x_offset = -int(w * pan_x * progress)
                return (x_offset, 'center')
        elif direction == "pan_right":
            def pos_func(t):
                progress = t / duration if duration > 0 else 0
                x_offset = int(w * pan_x * progress)
                return (x_offset, 'center')
        elif direction == "pan_up":
            def pos_func(t):
                progress = t / duration if duration > 0 else 0
                y_offset = -int(h * pan_y * progress)
                return ('center', y_offset)
        elif direction == "pan_down":
            def pos_func(t):
                progress = t / duration if duration > 0 else 0
                y_offset = int(h * pan_y * progress)
                return ('center', y_offset)
        else:
            pos_func = lambda t: ('center', 'center')
        
        clip = clip.set_position(pos_func)
        logger.info(f"Applied pan: {direction}")
    else:
        clip = clip.set_position(('center', 'center'))
    
    return clip