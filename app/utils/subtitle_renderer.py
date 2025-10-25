from typing import List, Dict, Tuple
from moviepy.editor import CompositeVideoClip, ImageClip
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import config
from utils.logger import get_logger

logger = get_logger(__name__)

# Global cache for rendered text images
_TEXT_CACHE = {}


def prerender_all_words(words: List[Dict]) -> Dict[str, Tuple[np.ndarray, Tuple[int, int]]]:
    """
    Pre-render all unique words at once to avoid repeated rendering
    
    Args:
        words: List of word dictionaries
        
    Returns:
        Dictionary mapping word -> (image_array, (width, height))
    """
    unique_words = set(w['word'].strip() for w in words if w['word'].strip())
    cache = {}
    
    logger.info(f"Pre-rendering {len(unique_words)} unique words")
    
    # Load font once
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/montserrat/Montserrat-Bold.ttf", 
            config.SUBTITLE_FONT_SIZE
        )
    except:
        try:
            font = ImageFont.truetype("Montserrat-Bold.ttf", config.SUBTITLE_FONT_SIZE)
        except:
            font = ImageFont.load_default()
    
    # Color mapping
    color_map = {
        'white': (255, 255, 255, 255),
        'yellow': (255, 255, 0, 255),
        'black': (0, 0, 0, 255)
    }
    text_color = color_map.get(config.SUBTITLE_COLOR, (255, 255, 255, 255))
    stroke_color = color_map.get(config.SUBTITLE_OUTLINE_COLOR, (0, 0, 0, 255))
    
    for word in unique_words:
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
        
        cache[word] = (np.array(img), (text_width, text_height))
    
    logger.info(f"Pre-rendering complete. Cache size: {len(cache)} words")
    return cache


def render_subtitles(video_clip, words: List[Dict], video_size: tuple) -> CompositeVideoClip:
    """
    Render word-by-word subtitles with optimized pre-rendering
    
    Args:
        video_clip: Base video clip
        words: List of word dictionaries with 'word', 'start', 'end' keys
        video_size: Tuple of (width, height)
    
    Returns:
        CompositeVideoClip with subtitles
    """
    if not words:
        logger.warning("No words provided for subtitles")
        return video_clip
    
    logger.info(f"Rendering {len(words)} word-by-word subtitles (optimized)")
    
    width, height = video_size
    
    # Pre-render all unique words at once
    word_cache = prerender_all_words(words)
    
    subtitle_clips = []
    
    for i, word_data in enumerate(words):
        word = word_data['word'].strip()
        start_time = word_data['start']
        end_time = word_data['end']
        duration = end_time - start_time
        
        if not word or word not in word_cache:
            continue
        
        # Get pre-rendered word
        word_img, (word_width, word_height) = word_cache[word]
        
        # Calculate center position
        subtitle_x = (width - word_img.shape[1]) // 2
        subtitle_y_pos = (height - word_img.shape[0]) // 2
        
        # Create clip for this word (reuse array)
        word_clip = ImageClip(word_img, transparent=True, duration=duration)
        word_clip = word_clip.set_position((subtitle_x, subtitle_y_pos))
        word_clip = word_clip.set_start(start_time)
        
        subtitle_clips.append(word_clip)
    
    logger.info(f"Created {len(subtitle_clips)} subtitle clips from cache")
    
    if subtitle_clips:
        return CompositeVideoClip([video_clip] + subtitle_clips)
    else:
        return video_clip