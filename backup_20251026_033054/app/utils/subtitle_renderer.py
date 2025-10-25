"""
Subtitle renderer - MAXIMUM OPTIMIZATION with aggressive caching
"""
from typing import List, Dict, Tuple
from moviepy.editor import CompositeVideoClip, ImageClip
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import hashlib
import config
from utils.logger import get_logger

logger = get_logger(__name__)

# GLOBAL persistent cache across all videos
_GLOBAL_WORD_CACHE = {}
_FONT_CACHE = None


def get_font():
    """Get font with caching"""
    global _FONT_CACHE
    
    if _FONT_CACHE is None:
        try:
            _FONT_CACHE = ImageFont.truetype(
                "/usr/share/fonts/truetype/montserrat/Montserrat-Bold.ttf", 
                config.SUBTITLE_FONT_SIZE
            )
        except:
            try:
                _FONT_CACHE = ImageFont.truetype(
                    "Montserrat-Bold.ttf", 
                    config.SUBTITLE_FONT_SIZE
                )
            except:
                _FONT_CACHE = ImageFont.load_default()
    
    return _FONT_CACHE


def get_word_cache_key(word: str) -> str:
    """Generate cache key for word"""
    return hashlib.md5(
        f"{word}_{config.SUBTITLE_FONT_SIZE}_{config.SUBTITLE_COLOR}_{config.SUBTITLE_OUTLINE_WIDTH}".encode()
    ).hexdigest()


def render_single_word(word: str, font) -> Tuple[np.ndarray, Tuple[int, int]]:
    """
    Render single word with MAXIMUM optimization
    
    Returns:
        (image_array, (width, height))
    """
    # Check global cache first
    cache_key = get_word_cache_key(word)
    
    if cache_key in _GLOBAL_WORD_CACHE:
        return _GLOBAL_WORD_CACHE[cache_key]
    
    # Color mapping
    color_map = {
        'white': (255, 255, 255, 255),
        'yellow': (255, 255, 0, 255),
        'black': (0, 0, 0, 255)
    }
    text_color = color_map.get(config.SUBTITLE_COLOR, (255, 255, 255, 255))
    stroke_color = color_map.get(config.SUBTITLE_OUTLINE_COLOR, (0, 0, 0, 255))
    
    # Get text dimensions
    temp_img = Image.new('RGBA', (1, 1))
    temp_draw = ImageDraw.Draw(temp_img)
    bbox = temp_draw.textbbox(
        (0, 0), 
        word, 
        font=font, 
        stroke_width=config.SUBTITLE_OUTLINE_WIDTH
    )
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Add padding
    padding = config.SUBTITLE_OUTLINE_WIDTH * 2
    img_width = text_width + padding * 2
    img_height = text_height + padding * 2
    
    # Create image with transparency
    img = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw text with outline
    draw.text(
        (padding - bbox[0], padding - bbox[1]),
        word,
        font=font,
        fill=text_color,
        stroke_width=config.SUBTITLE_OUTLINE_WIDTH,
        stroke_fill=stroke_color
    )
    
    # Convert to numpy and cache
    result = (np.array(img), (text_width, text_height))
    _GLOBAL_WORD_CACHE[cache_key] = result
    
    return result


def prerender_words_batch(words: List[Dict], font) -> Dict[str, Tuple[np.ndarray, Tuple[int, int]]]:
    """
    Pre-render words in batch with global caching
    
    Returns:
        Dict mapping word -> (image_array, dimensions)
    """
    unique_words = set(w['word'].strip() for w in words if w['word'].strip())
    
    # Filter out already cached words
    words_to_render = [w for w in unique_words if get_word_cache_key(w) not in _GLOBAL_WORD_CACHE]
    
    if words_to_render:
        logger.info(f"Rendering {len(words_to_render)} new words (cache: {len(_GLOBAL_WORD_CACHE)} words)")
    else:
        logger.info(f"All words cached ({len(unique_words)} words)")
    
    # Render new words
    for word in words_to_render:
        render_single_word(word, font)
    
    # Return all requested words from cache
    result = {}
    for word in unique_words:
        cache_key = get_word_cache_key(word)
        if cache_key in _GLOBAL_WORD_CACHE:
            result[word] = _GLOBAL_WORD_CACHE[cache_key]
    
    return result


def create_subtitle_clips_optimized(
    words: List[Dict], 
    video_size: Tuple[int, int],
    word_cache: Dict[str, Tuple[np.ndarray, Tuple[int, int]]]
) -> List[ImageClip]:
    """
    Create subtitle clips with MAXIMUM optimization
    
    Key optimizations:
    - Reuse cached word images
    - Minimal ImageClip creation
    - Pre-calculated positions
    """
    width, height = video_size
    subtitle_clips = []
    
    for word_data in words:
        word = word_data['word'].strip()
        start_time = word_data['start']
        end_time = word_data['end']
        duration = end_time - start_time
        
        if not word or word not in word_cache:
            continue
        
        # Get cached word image
        word_img, (word_width, word_height) = word_cache[word]
        
        # Pre-calculate position
        subtitle_x = (width - word_img.shape[1]) // 2
        subtitle_y = (height - word_img.shape[0]) // 2
        
        # Create clip with cached image
        word_clip = ImageClip(word_img, transparent=True, duration=duration)
        word_clip = word_clip.set_position((subtitle_x, subtitle_y))
        word_clip = word_clip.set_start(start_time)
        
        subtitle_clips.append(word_clip)
    
    return subtitle_clips


def render_subtitles(video_clip, words: List[Dict], video_size: tuple) -> CompositeVideoClip:
    """
    Render word-by-word subtitles with MAXIMUM optimization
    
    Optimizations:
    - Global persistent cache across videos
    - Batch pre-rendering
    - Fast position calculations
    - Minimal memory allocations
    """
    if not words:
        logger.warning("No words provided for subtitles")
        return video_clip
    
    logger.info(f"Rendering {len(words)} word-by-word subtitles (optimized)")
    
    # Get cached font
    font = get_font()
    
    # Pre-render all words (uses global cache)
    word_cache = prerender_words_batch(words, font)
    
    # Create subtitle clips efficiently
    subtitle_clips = create_subtitle_clips_optimized(words, video_size, word_cache)
    
    logger.info(f"Created {len(subtitle_clips)} subtitle clips (cache size: {len(_GLOBAL_WORD_CACHE)})")
    
    if subtitle_clips:
        return CompositeVideoClip([video_clip] + subtitle_clips)
    else:
        return video_clip


def clear_subtitle_cache():
    """Clear global subtitle cache (optional memory management)"""
    global _GLOBAL_WORD_CACHE
    cache_size = len(_GLOBAL_WORD_CACHE)
    _GLOBAL_WORD_CACHE.clear()
    logger.info(f"Cleared subtitle cache ({cache_size} words)")