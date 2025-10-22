"""
TikTok-style subtitle rendering - proper implementation
"""
from typing import List, Dict
from moviepy.editor import CompositeVideoClip, TextClip
import config
from utils.logger import get_logger

logger = get_logger(__name__)

def group_words_strict(words: List[Dict], min_words: int = 2, max_words: int = 4) -> List[Dict]:
    """Group words strictly 2-4 per chunk"""
    if not words:
        return []
    
    groups = []
    i = 0
    
    while i < len(words):
        chunk_size = min(max_words, len(words) - i)
        if chunk_size < min_words and i > 0:
            for w in words[i:]:
                groups[-1]['words'].append(w)
            break
        
        chunk = words[i:i+chunk_size]
        groups.append({
            'words': chunk,
            'start': chunk[0]['start'],
            'end': chunk[-1]['end']
        })
        i += chunk_size
    
    return groups

def render_subtitles(video_clip, words: List[Dict], video_size: tuple) -> CompositeVideoClip:
    """
    Render TikTok-style subtitles: 2-4 words, center, current word yellow
    Optimized for speed: cache measurements, minimize clip creation
    """
    if not words:
        logger.warning("No words provided for subtitles")
        return video_clip
    
    word_groups = group_words_strict(words)
    logger.info(f"Rendering {len(word_groups)} subtitle groups (2-4 words each)")
    
    all_subtitle_clips = []
    width, height = video_size
    center_y = height // 2
    
    # Pre-cache text measurements for all unique words
    word_size_cache = {}
    
    for group in word_groups:
        group_words = group['words']
        
        # Measure words (cached)
        word_sizes = []
        for word_data in group_words:
            word = word_data['word']
            if word not in word_size_cache:
                measure_clip = TextClip(
                    word,
                    fontsize=config.SUBTITLE_FONT_SIZE,
                    color='white',
                    font=config.SUBTITLE_FONT
                )
                word_size_cache[word] = measure_clip.size
                measure_clip.close()
            word_sizes.append(word_size_cache[word])
        
        # Calculate total width with spaces
        space_width = word_sizes[0][0] // 4 if word_sizes else 10
        total_width = sum(w for w, h in word_sizes) + space_width * (len(word_sizes) - 1)
        start_x = (width - total_width) // 2
        
        current_x = start_x
        word_height = word_sizes[0][1] if word_sizes else config.SUBTITLE_FONT_SIZE
        
        for i, word_data in enumerate(group_words):
            word = word_data['word']
            word_start = word_data['start']
            word_duration = word_data['end'] - word_data['start']
            word_width = word_sizes[i][0]
            
            # Reuse common parameters
            common_params = {
                'fontsize': config.SUBTITLE_FONT_SIZE,
                'font': config.SUBTITLE_FONT,
                'stroke_color': config.SUBTITLE_OUTLINE_COLOR,
                'stroke_width': config.SUBTITLE_OUTLINE_WIDTH
            }
            
            # White base
            white_clip = TextClip(
                word,
                color='white',
                **common_params
            ).set_position((current_x, center_y - word_height//2)).set_start(group['start']).set_duration(group['end'] - group['start'])
            
            # Yellow highlight
            yellow_clip = TextClip(
                word,
                color='yellow',
                **common_params
            ).set_position((current_x, center_y - word_height//2)).set_start(word_start).set_duration(word_duration)
            
            all_subtitle_clips.extend([white_clip, yellow_clip])
            current_x += word_width + space_width
    
    logger.info(f"Created {len(all_subtitle_clips)} subtitle clips")
    return CompositeVideoClip([video_clip] + all_subtitle_clips) if all_subtitle_clips else video_clip