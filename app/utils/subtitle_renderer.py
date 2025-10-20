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
    """Create text image using PIL"""
    width, height = video_size
    img = Image.new('RGBA', (width, 200), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", fontsize)
    except:
        font = ImageFont.load_default()
    
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (width - text_width) // 2
    y = (200 - text_height) // 2
    
    color_map = {'yellow': (255, 255, 0), 'white': (255, 255, 255), 'black': (0, 0, 0)}
    text_rgb = color_map.get(color, (255, 255, 255))
    stroke_rgb = color_map.get(stroke_color, (0, 0, 0))
    
    draw.text((x, y), text, font=font, fill=text_rgb + (255,), 
              stroke_width=stroke_width, stroke_fill=stroke_rgb + (255,))
    
    # Convert RGBA to RGB with alpha compositing
    rgb_img = Image.new('RGB', (width, 200), (0, 0, 0))
    rgb_img.paste(img, mask=img.split()[3])
    
    return np.array(rgb_img)


def render_subtitles(video_clip, words: List[Dict], video_size: tuple) -> CompositeVideoClip:
    """Render word-by-word subtitles"""
    if not words:
        logger.warning("No words provided for subtitles")
        return video_clip
    
    logger.info(f"Rendering {len(words)} word subtitles using PIL")
    
    subtitle_clips = []
    width, height = video_size
    y_position = int(height * config.SUBTITLE_POSITION[1])
    
    for word_data in words:
        word = word_data['word']
        start = word_data['start']
        duration = word_data['end'] - word_data['start']
        
        try:
            text_img = create_text_image(word, video_size, config.SUBTITLE_HIGHLIGHT_SIZE,
                                        config.SUBTITLE_HIGHLIGHT_COLOR, 
                                        config.SUBTITLE_OUTLINE_COLOR,
                                        config.SUBTITLE_OUTLINE_WIDTH)
            
            clip = VideoClip(lambda t, img=text_img: img, duration=duration)
            clip = clip.set_start(start).set_position(('center', y_position))
            subtitle_clips.append(clip)
            
        except Exception as e:
            logger.error(f"Failed to create subtitle for word '{word}': {e}")
    
    logger.info(f"Created {len(subtitle_clips)} subtitle clips")
    
    if not subtitle_clips:
        return video_clip
    
    return CompositeVideoClip([video_clip] + subtitle_clips)