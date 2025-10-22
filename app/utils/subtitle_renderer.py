from typing import List, Dict
from moviepy.editor import CompositeVideoClip, ImageClip
from PIL import Image, ImageDraw, ImageFont
import numpy as np
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


def create_text_image_transparent(text: str, fontsize: int, color: str, outline_color: str, outline_width: int) -> tuple:
    """Create high-quality text image with transparency"""
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/montserrat/Montserrat-Bold.ttf", fontsize)
    except:
        try:
            font = ImageFont.truetype("Montserrat-Bold.ttf", fontsize)
        except:
            font = ImageFont.load_default()
    
    temp_img = Image.new('RGBA', (1, 1))
    temp_draw = ImageDraw.Draw(temp_img)
    bbox = temp_draw.textbbox((0, 0), text, font=font, stroke_width=outline_width)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    padding = outline_width * 2
    img_width = text_width + padding * 2
    img_height = text_height + padding * 2
    
    img = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    color_map = {'white': (255, 255, 255), 'yellow': (255, 255, 0), 'black': (0, 0, 0)}
    text_color = color_map.get(color, (255, 255, 255))
    stroke_color = color_map.get(outline_color, (0, 0, 0))
    
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
    Render TikTok-style subtitles with transparency
    """
    if not words:
        logger.warning("No words provided for subtitles")
        return video_clip
    
    word_groups = group_words_strict(words)
    logger.info(f"Rendering {len(word_groups)} subtitle groups (2-4 words each)")
    
    all_subtitle_clips = []
    width, height = video_size
    max_width = int(width * 0.85)
    
    word_cache = {}
    
    space_img, (space_width, _) = create_text_image_transparent(
        " ",
        config.SUBTITLE_FONT_SIZE,
        'white',
        config.SUBTITLE_OUTLINE_COLOR,
        config.SUBTITLE_OUTLINE_WIDTH
    )
    
    for group in word_groups:
        group_words = group['words']
        group_start = group['start']
        group_end = group['end']
        
        word_data_list = []
        for word_data in group_words:
            word = word_data['word']
            if word not in word_cache:
                white_img, size = create_text_image_transparent(
                    word,
                    config.SUBTITLE_FONT_SIZE,
                    'white',
                    config.SUBTITLE_OUTLINE_COLOR,
                    config.SUBTITLE_OUTLINE_WIDTH
                )
                yellow_img, _ = create_text_image_transparent(
                    word,
                    config.SUBTITLE_FONT_SIZE,
                    'yellow',
                    config.SUBTITLE_OUTLINE_COLOR,
                    config.SUBTITLE_OUTLINE_WIDTH
                )
                word_cache[word] = {
                    'white': white_img,
                    'yellow': yellow_img,
                    'size': size
                }
            
            word_data_list.append({
                'word': word,
                'start': word_data['start'],
                'end': word_data['end'],
                'size': word_cache[word]['size'],
                'white_img': word_cache[word]['white'],
                'yellow_img': word_cache[word]['yellow']
            })
        
        lines = []
        current_line = []
        current_line_width = 0
        
        for i, wd in enumerate(word_data_list):
            word_with_space = wd['size'][0] + (space_width if current_line else 0)
            
            if current_line_width + word_with_space > max_width and current_line:
                lines.append(current_line)
                current_line = [i]
                current_line_width = wd['size'][0]
            else:
                current_line.append(i)
                current_line_width += word_with_space
        
        if current_line:
            lines.append(current_line)
        
        # Find max height across all words for alignment
        max_word_height = max(wd['white_img'].shape[0] for wd in word_data_list)
        
        line_spacing = int(max_word_height * config.SUBTITLE_LINE_SPACING)
        total_height = len(lines) * max_word_height + (len(lines) - 1) * line_spacing
        start_y = (height - total_height) // 2
        
        for line_idx, line_word_indices in enumerate(lines):
            line_words = [word_data_list[i] for i in line_word_indices]
            
            line_width = sum(wd['size'][0] for wd in line_words) + space_width * (len(line_words) - 1)
            start_x = (width - line_width) // 2
            current_x = start_x
            line_y = start_y + line_idx * (max_word_height + line_spacing)
            
            for wd in line_words:
                # Vertical alignment: align baselines
                word_img_height = wd['white_img'].shape[0]
                vertical_offset = max_word_height - word_img_height
                current_y = line_y + vertical_offset
                
                white_clip = ImageClip(wd['white_img'], transparent=True)
                white_clip = white_clip.set_duration(group_end - group_start)
                white_clip = white_clip.set_position((current_x, current_y))
                white_clip = white_clip.set_start(group_start)
                
                yellow_clip = ImageClip(wd['yellow_img'], transparent=True)
                yellow_clip = yellow_clip.set_duration(wd['end'] - wd['start'])
                yellow_clip = yellow_clip.set_position((current_x, current_y))
                yellow_clip = yellow_clip.set_start(wd['start'])
                
                all_subtitle_clips.extend([white_clip, yellow_clip])
                current_x += wd['size'][0] + space_width
    
    logger.info(f"Created {len(all_subtitle_clips)} subtitle clips")
    return CompositeVideoClip([video_clip] + all_subtitle_clips) if all_subtitle_clips else video_clip