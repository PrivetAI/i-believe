"""
Ken Burns effect - MAXIMUM OPTIMIZATION with pre-calculated trajectories
"""
import sys
from pathlib import Path
import random
from typing import Dict, List, Tuple
import numpy as np
from scipy.ndimage import zoom as scipy_zoom

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from utils.logger import get_logger

logger = get_logger(__name__)


def generate_ken_burns_params() -> Dict:
    """Generate Ken Burns parameters"""
    direction = random.choice(config.KEN_BURNS_DIRECTIONS)
    
    zoom_start = random.uniform(*config.KEN_BURNS_ZOOM_RANGE)
    zoom_end = random.uniform(*config.KEN_BURNS_ZOOM_RANGE)
    
    if abs(zoom_end - zoom_start) < 0.1:
        zoom_end = zoom_start + 0.15
    
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


def precalculate_trajectory(params: Dict, duration: float, fps: int) -> List[Dict]:
    """
    Pre-calculate entire Ken Burns trajectory to avoid per-frame calculations
    
    Args:
        params: Ken Burns parameters
        duration: Clip duration in seconds
        fps: Frames per second
        
    Returns:
        List of frame states (zoom, x_offset, y_offset)
    """
    direction = params['direction']
    zoom_start = params['zoom_start']
    zoom_end = params['zoom_end']
    pan_x = params['pan_x']
    pan_y = params['pan_y']
    
    num_frames = int(duration * fps)
    zoom_diff = zoom_end - zoom_start
    
    # Determine pan factors
    pan_x_factor = 0
    pan_y_factor = 0
    
    if direction == "pan_left":
        pan_x_factor = pan_x
    elif direction == "pan_right":
        pan_x_factor = -pan_x
    
    trajectory = []
    
    for frame_idx in range(num_frames):
        progress = frame_idx / max(num_frames - 1, 1)
        zoom = zoom_start + zoom_diff * progress
        
        # Pre-calculate offsets based on direction
        trajectory.append({
            'zoom': zoom,
            'pan_x_factor': pan_x_factor * progress,
            'pan_y_factor': pan_y_factor * progress
        })
    
    return trajectory


def resize_frame_numpy(frame: np.ndarray, scale: float) -> np.ndarray:
    """Ultra-fast frame resize with minimal quality loss"""
    if abs(scale - 1.0) < 0.01:
        return frame
    
    # Use order=1 (bilinear) for maximum speed
    return scipy_zoom(frame, (scale, scale, 1), order=1, prefilter=False)


def apply_ken_burns_optimized(clip, params: Dict, duration: float):
    """
    Apply Ken Burns with pre-calculated trajectory (MAXIMUM SPEED)
    
    Key optimizations:
    - Pre-calculate all zoom/pan values
    - Lookup table instead of per-frame calculations
    - Minimal numpy operations
    - Fast interpolation
    """
    w, h = clip.size
    fps = clip.fps if hasattr(clip, 'fps') else config.DEFAULT_FPS
    
    logger.info(f"Pre-calculating Ken Burns trajectory: {params['direction']}")
    
    # PRE-CALCULATE entire trajectory
    trajectory = precalculate_trajectory(params, duration, fps)
    
    direction = params['direction']
    
    def effect(get_frame, t):
        # Lookup pre-calculated values (O(1) operation)
        frame_idx = min(int(t * fps), len(trajectory) - 1)
        state = trajectory[frame_idx]
        
        frame = get_frame(t)
        zoom = state['zoom']
        
        # Fast resize (optimized scipy)
        zoomed = resize_frame_numpy(frame, zoom)
        zoomed_h, zoomed_w = zoomed.shape[:2]
        
        # Calculate offsets with pre-calculated factors
        if direction in ["pan_left", "pan_right"]:
            max_x = max(0, zoomed_w - w)
            x_offset = int(max_x * (0.5 + state['pan_x_factor']))
            y_offset = (zoomed_h - h) // 2
        else:
            x_offset = (zoomed_w - w) // 2
            y_offset = (zoomed_h - h) // 2
        
        # Clamp and crop (fast numpy slicing)
        x_offset = max(0, min(x_offset, zoomed_w - w))
        y_offset = max(0, min(y_offset, zoomed_h - h))
        
        return zoomed[y_offset:y_offset+h, x_offset:x_offset+w]
    
    return clip.fl(effect)


# Alias for backward compatibility
apply_ken_burns = apply_ken_burns_optimized