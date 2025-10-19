"""
Subtitle rendering with word-by-word live caption style
"""
from typing import List, Dict
from moviepy.editor import TextClip, CompositeVideoClip
import config
from utils.logger import get_logger

logger = get_logger(__name__)


def render_subtitles(video_clip, words: List[Dict], video_size: tuple) -> CompositeVideoClip:
    """
    Render word-by-word subtitles with live caption style
    
    Each word appears individually, synchronized with audio timing
    
    Args:
        video_clip: Base video clip
        words: List of word dictionaries with 'word', 'start', 'end' keys
        video_size: Tuple of (width, height)
        
    Returns:
        CompositeVideoClip with subtitle overlay
    """
    if not words:
        logger.warning("No words provided for subtitles")
        return video_clip
    
    logger.info(f"Rendering {len(words)} word subtitles")
    
    subtitle_clips = []
    width, height = video_size
    
    # Calculate position based on config
    y_position = int(height * config.SUBTITLE_POSITION[1])
    
    for i, word_data in enumerate(words):
        word = word_data['word']
        start = word_data['start']
        end = word_data['end']
        duration = end - start
        
        try:
            # Create text clip for current word with highlight style
            txt_clip = TextClip(
                word,
                fontsize=config.SUBTITLE_HIGHLIGHT_SIZE,
                color=config.SUBTITLE_HIGHLIGHT_COLOR,
                font=config.SUBTITLE_FONT,
                stroke_color=config.SUBTITLE_OUTLINE_COLOR,
                stroke_width=config.SUBTITLE_OUTLINE_WIDTH,
                method='caption',
                size=(width * 0.8, None),
                align='center'
            )
            
            # Set timing and position
            txt_clip = txt_clip.set_start(start)
            txt_clip = txt_clip.set_duration(duration)
            txt_clip = txt_clip.set_position(('center', y_position))
            
            subtitle_clips.append(txt_clip)
            
        except Exception as e:
            logger.error(f"Failed to create subtitle for word '{word}': {e}")
            continue
    
    logger.info(f"Created {len(subtitle_clips)} subtitle clips")
    
    # Composite video with subtitles
    final_clip = CompositeVideoClip([video_clip] + subtitle_clips)
    
    return final_clip