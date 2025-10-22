from typing import List, Dict
from moviepy.editor import CompositeVideoClip, ImageClip
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import config
from utils.logger import get_logger

logger = get_logger(__name__)


def create_text_image_transparent(text: str, fontsize: int, color: str, outline_color: str, outline_width: int) -> tuple:
    """Create high-quality text image with transparency"""
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/montserrat/Montserrat-Bold.ttf", fontsize)
    except:
        try:
            font = ImageFont.truetype("Montserrat-Bold.ttf", fontsize)
        except:
            font = ImageFont.load_default()
    
    # Get text dimensions
    temp_img = Image.new('RGBA', (1, 1))
    temp_draw = ImageDraw.Draw(temp_img)
    bbox = temp_draw.textbbox((0, 0), text, font=font, stroke_width=outline_width)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Add padding for outline
    padding = outline_width * 2
    img_width = text_width + padding * 2
    img_height = text_height + padding * 2
    
    # Create image with transparency
    img = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Color mapping
    color_map = {
        'white': (255, 255, 255, 255),
        'yellow': (255, 255, 0, 255),
        'black': (0, 0, 0, 255)
    }
    text_color = color_map.get(color, (255, 255, 255, 255))
    stroke_color = color_map.get(outline_color, (0, 0, 0, 255))
    
    # Draw text with outline
    draw.text(
        (padding - bbox[0], padding - bbox[1]),
        text,
        font=font,
        fill=text_color,
        stroke_width=outline_width,
        stroke_fill=stroke_color
    )
    
    return np.array(img), (text_width, text_height)


def render_subtitles(video_clip, words: List[Dict], video_size: tuple) -> CompositeVideoClip:
    """
    Render word-by-word subtitles with highlight effect
    Each word appears individually at the center of the screen
    
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
    
    logger.info(f"Rendering {len(words)} word-by-word subtitles")
    
    width, height = video_size
    
    # Calculate vertical position (80% down from top)
    subtitle_y = int(height * 0.8)
    
    subtitle_clips = []
    word_cache = {}
    
    for i, word_data in enumerate(words):
        word = word_data['word'].strip()
        start_time = word_data['start']
        end_time = word_data['end']
        duration = end_time - start_time
        
        # Skip empty words
        if not word:
            continue
        
        # Generate or retrieve from cache
        if word not in word_cache:
            # Create yellow (highlighted) version
            yellow_img, size = create_text_image_transparent(
                word,
                config.SUBTITLE_FONT_SIZE,
                'yellow',
                config.SUBTITLE_OUTLINE_COLOR,
                config.SUBTITLE_OUTLINE_WIDTH
            )
            
            word_cache[word] = {
                'yellow': yellow_img,
                'size': size
            }
        
        # Get word image and size
        yellow_img = word_cache[word]['yellow']
        word_width, word_height = word_cache[word]['size']
        
        # Calculate horizontal center position
        subtitle_x = (width - yellow_img.shape[1]) // 2
        
        # Create clip for this word
        word_clip = ImageClip(yellow_img, transparent=True)
        word_clip = word_clip.set_duration(duration)
        word_clip = word_clip.set_position((subtitle_x, subtitle_y - word_height // 2))
        word_clip = word_clip.set_start(start_time)
        
        subtitle_clips.append(word_clip)
        
        logger.debug(f"Word {i+1}/{len(words)}: '{word}' at {start_time:.2f}s-{end_time:.2f}s")
    
    logger.info(f"Created {len(subtitle_clips)} subtitle clips")
    
    if subtitle_clips:
        return CompositeVideoClip([video_clip] + subtitle_clips)
    else:
        return video_clip