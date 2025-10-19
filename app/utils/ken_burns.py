"""
Ken Burns effect implementation
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
    zoom_start = random.uniform(*config.KEN_BURNS_ZOOM_RANGE)
    zoom_end = random.uniform(*config.KEN_BURNS_ZOOM_RANGE)
    pan_x = random.uniform(*config.KEN_BURNS_PAN_RANGE)
    pan_y = random.uniform(*config.KEN_BURNS_PAN_RANGE)
    
    params = {
        'direction': direction,
        'zoom_start': zoom_start,
        'zoom_end': zoom_end,
        'pan_x': pan_x,
        'pan_y': pan_y
    }
    
    logger.debug(f"Generated Ken Burns params: {params}")
    return params


def apply_ken_burns(clip, params: Dict, duration: float):
    """
    Apply Ken Burns effect to a clip
    
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
    logger.debug(f"Clip size: {w}x{h}, Duration: {duration}s")
    
    # Define resize function based on direction
    if 'zoom' in direction:
        if direction == "zoom_in":
            resize_func = lambda t: zoom_start + (zoom_end - zoom_start) * (t / duration)
        else:  # zoom_out
            resize_func = lambda t: zoom_end - (zoom_end - zoom_start) * (t / duration)
        
        clip = clip.resize(resize_func)
    
    # Define position function for panning
    if 'pan' in direction:
        if direction == "pan_left":
            pos_func = lambda t: (int(-w * pan_x * (t / duration)), 'center')
        elif direction == "pan_right":
            pos_func = lambda t: (int(w * pan_x * (t / duration)), 'center')
        elif direction == "pan_up":
            pos_func = lambda t: ('center', int(-h * pan_y * (t / duration)))
        elif direction == "pan_down":
            pos_func = lambda t: ('center', int(h * pan_y * (t / duration)))
        else:
            pos_func = lambda t: ('center', 'center')
        
        clip = clip.set_position(pos_func)
    else:
        clip = clip.set_position(('center', 'center'))
    
    return clip