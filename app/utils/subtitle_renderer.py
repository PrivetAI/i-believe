"""
Subtitle rendering with word-by-word live caption style using PIL
"""
from typing import List, Dict
from moviepy.editor import CompositeVideoClip, TextClip
import config
from utils.logger import get_logger

logger = get_logger(__name__)

def group_words_by_time(words: List[Dict], max_words: int = 3, max_duration: float = 2.0) -> List[Dict]:
    """Group words into chunks for display"""
    if not words:
        return []
    
    groups = []
    current_group = {
        'words': [words[0]['word']],
        'start': words[0]['start'],
        'end': words[0]['end']
    }
    
    for i in range(1, len(words)):
        word = words[i]
        duration = word['end'] - current_group['start']
        
        # Start new group if too many words or too long
        if len(current_group['words']) >= max_words or duration > max_duration:
            groups.append(current_group)
            current_group = {
                'words': [word['word']],
                'start': word['start'],
                'end': word['end']
            }
        else:
            # Add to current group
            current_group['words'].append(word['word'])
            current_group['end'] = word['end']
    
    # Add last group
    if current_group['words']:
        groups.append(current_group)
    
    return groups

def render_subtitles(video_clip, words: List[Dict], video_size: tuple) -> CompositeVideoClip:
    """Render grouped subtitles with fade-in effect"""
    if not words:
        logger.warning("No words provided for subtitles")
        return video_clip
    
    # Group words
    word_groups = group_words_by_time(words, max_words=3, max_duration=2.0)
    logger.info(f"Rendering {len(word_groups)} subtitle groups from {len(words)} words")
    
    subtitle_clips = []
    width, height = video_size
    y_position = int(height * config.SUBTITLE_POSITION[1])
    fade_duration = 0.2
    
    for group in word_groups:
        text = ' '.join(group['words'])
        start = group['start']
        duration = group['end'] - group['start']
        
        try:
            # Create text clip
            txt_clip = TextClip(
                text,
                fontsize=config.SUBTITLE_FONT_SIZE,
                color=config.SUBTITLE_HIGHLIGHT_COLOR,
                font='DejaVu-Sans-Bold',
                stroke_color=config.SUBTITLE_OUTLINE_COLOR,
                stroke_width=config.SUBTITLE_OUTLINE_WIDTH,
                method='caption',
                size=(width * 0.9, None),
                bg_color='transparent'
            )
            
            # Set duration and apply fade
            # txt_clip = txt_clip.set_duration(duration)
            # if duration > fade_duration:
                # txt_clip = txt_clip.fadein(fade_duration)
            
            # Position and timing
            txt_clip = txt_clip.set_position(('center', y_position)).set_start(start)
            subtitle_clips.append(txt_clip)
            
        except Exception as e:
            logger.error(f"Failed to create subtitle for text '{text}': {e}")
            continue
    
    logger.info(f"Created {len(subtitle_clips)} subtitle clips")
    
    if not subtitle_clips:
        return video_clip
    
    return CompositeVideoClip([video_clip] + subtitle_clips)