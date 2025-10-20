"""
Subtitle rendering with word-by-word live caption style using PIL
"""
from typing import List, Dict
from moviepy.editor import CompositeVideoClip, VideoClip
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import config
from utils.logger import get_logger

logger = get_logger(__name__)


def create_text_image(text: str, video_size: tuple, fontsize: int, color: str, 
                      stroke_color: str, stroke_width: int) -> np.ndarray:
    """
    Create text image using PIL instead of ImageMagick
    
    Args:
        text: Text to render
        video_size: Video dimensions (width, height)
        fontsize: Font size
        color: Text color
        stroke_color: Outline color
        stroke_width: Outline width
        
    Returns:
        Numpy array of RGBA image
    """
    width, height = video_size
    
    # Create transparent image
    img = Image.new('RGBA', (width, 200), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Try to load font, fallback to default
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", fontsize)
    except:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", fontsize)
        except:
            font = ImageFont.load_default()
    
    # Get text bounding box
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Calculate center position
    x = (width - text_width) // 2
    y = (200 - text_height) // 2
    
    # Convert color names to RGB
    color_map = {
        'yellow': (255, 255, 0),
        'white': (255, 255, 255),
        'black': (0, 0, 0)
    }
    
    text_rgb = color_map.get(color, (255, 255, 255))
    stroke_rgb = color_map.get(stroke_color, (0, 0, 0))
    
    # Draw text with outline
    draw.text((x, y), text, font=font, fill=text_rgb + (255,), 
              stroke_width=stroke_width, stroke_fill=stroke_rgb + (255,))
    
    return np.array(img)


def make_text_clip(text: str, start: float, duration: float, video_size: tuple, 
                   y_position: int) -> VideoClip:
    """
    Create a text clip using PIL-generated images
    
    Args:
        text: Text to display
        start: Start time in seconds
        duration: Duration in seconds
        video_size: Video dimensions
        y_position: Vertical position
        
    Returns:
        VideoClip with text overlay
    """
    # Create text image
    text_img = create_text_image(
        text,
        video_size,
        config.SUBTITLE_HIGHLIGHT_SIZE,
        config.SUBTITLE_HIGHLIGHT_COLOR,
        config.SUBTITLE_OUTLINE_COLOR,
        config.SUBTITLE_OUTLINE_WIDTH
    )
    
    def make_frame(t):
        return text_img
    
    # Create clip
    clip = VideoClip(make_frame, duration=duration)
    clip = clip.set_start(start)
    clip = clip.set_position(('center', y_position))
    
    return clip


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
    
    logger.info(f"Rendering {len(words)} word subtitles using PIL")
    
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
            # Create text clip using PIL
            txt_clip = make_text_clip(word, start, duration, video_size, y_position)
            subtitle_clips.append(txt_clip)
            
        except Exception as e:
            logger.error(f"Failed to create subtitle for word '{word}': {e}")
            continue
    
    logger.info(f"Created {len(subtitle_clips)} subtitle clips")
    
    if not subtitle_clips:
        logger.warning("No subtitle clips created, returning original video")
        return video_clip
    
    # Composite video with subtitles
    final_clip = CompositeVideoClip([video_clip] + subtitle_clips)
    
    return final_clip