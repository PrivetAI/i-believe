"""
Ken Burns effect implementation
"""
import sys
from pathlib import Path
import random
from typing import Dict
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from utils.logger import get_logger

logger = get_logger(__name__)


def generate_ken_burns_params() -> Dict:
    """Generate Ken Burns parameters from config ranges"""
    direction = random.choice(config.KEN_BURNS_DIRECTIONS)
    
    zoom_start = random.uniform(*config.KEN_BURNS_ZOOM_RANGE)
    zoom_end = random.uniform(*config.KEN_BURNS_ZOOM_RANGE)
    
    # Ensure zoom difference is visible
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


def apply_ken_burns(clip, params: Dict, duration: float):
    """
    Apply Ken Burns effect with parameters from config
    Optimized: pre-calculate values, minimize operations per frame
    """
    direction = params['direction']
    zoom_start = params['zoom_start']
    zoom_end = params['zoom_end']
    pan_x = params['pan_x']
    pan_y = params['pan_y']
    
    w, h = clip.size
    
    logger.info(f"Applying Ken Burns: {direction}, zoom {zoom_start:.2f}->{zoom_end:.2f}")
    
    # Pre-calculate constants
    zoom_diff = zoom_end - zoom_start
    
    # Determine pan offsets based on direction
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
        
        # Resize
        from PIL import Image
        img = Image.fromarray(frame)
        new_w = int(w * zoom)
        new_h = int(h * zoom)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        zoomed = np.array(img)
        
        # Calculate offsets
        if direction in ["pan_left", "pan_right"]:
            max_x = max(0, zoomed.shape[1] - w)
            x_offset = int(max_x * (0.5 + pan_x_factor * progress))
            y_offset = (zoomed.shape[0] - h) // 2
        elif direction in ["pan_up", "pan_down"]:
            x_offset = (zoomed.shape[1] - w) // 2
            max_y = max(0, zoomed.shape[0] - h)
            y_offset = int(max_y * (0.5 + pan_y_factor * progress))
        else:
            x_offset = (zoomed.shape[1] - w) // 2
            y_offset = (zoomed.shape[0] - h) // 2
        
        # Clamp offsets
        x_offset = max(0, min(x_offset, zoomed.shape[1] - w))
        y_offset = max(0, min(y_offset, zoomed.shape[0] - h))
        
        # Crop
        return zoomed[y_offset:y_offset+h, x_offset:x_offset+w]
    
    return clip.fl(effect)