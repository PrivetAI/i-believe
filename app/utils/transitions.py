"""
Video transition effects
"""
import sys
from pathlib import Path
import random
from typing import List
from moviepy.editor import VideoClip, CompositeVideoClip, concatenate_videoclips

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from utils.logger import get_logger

logger = get_logger(__name__)


def apply_fade_transition(clip1: VideoClip, clip2: VideoClip, duration: float) -> VideoClip:
    """Apply fade transition between two clips"""
    clip1 = clip1.fadeout(duration)
    clip2 = clip2.fadein(duration)
    return concatenate_videoclips([clip1, clip2], method="compose")


def apply_crossfade_transition(clip1: VideoClip, clip2: VideoClip, duration: float) -> VideoClip:
    """Apply crossfade transition between two clips"""
    clip1 = clip1.crossfadeout(duration)
    clip2 = clip2.crossfadein(duration)
    return concatenate_videoclips([clip1, clip2], padding=-duration)


def apply_transitions(clips: List[VideoClip]) -> VideoClip:
    """
    Apply random transitions between clips
    
    Args:
        clips: List of video clips
        
    Returns:
        Single video clip with transitions applied
    """
    if len(clips) <= 1:
        logger.info("Only one clip, no transitions needed")
        return clips[0] if clips else None
    
    logger.info(f"Applying transitions between {len(clips)} clips")
    
    result_clips = []
    
    for i in range(len(clips)):
        clip = clips[i]
        
        if i > 0:
            transition_type = random.choice(config.TRANSITION_TYPES)
            logger.debug(f"Transition {i}: {transition_type}")
            
            clip = clip.crossfadein(config.TRANSITION_DURATION)
            result_clips[-1] = result_clips[-1].crossfadeout(config.TRANSITION_DURATION)
        
        result_clips.append(clip)
    
    final_clip = concatenate_videoclips(result_clips, padding=-config.TRANSITION_DURATION, method="compose")
    
    logger.info("Transitions applied successfully")
    return final_clip