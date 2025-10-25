"""
Frame Generator - Generates video frames with all effects
Replaces MoviePy clip composition
"""
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Generator
from PIL import Image
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from models.slide import Slide
from utils.ken_burns import generate_ken_burns_params, precalculate_trajectory, resize_frame_numpy
from utils.subtitle_renderer import prerender_words_batch, get_font
from utils import transitions
from utils.logger import get_logger

logger = get_logger(__name__)


class FrameGenerator:
    """Generates video frames with all effects applied"""
    
    def __init__(self, resolution: Tuple[int, int], fps: int = None):
        """
        Initialize frame generator
        
        Args:
            resolution: (width, height)
            fps: Frames per second
        """
        self.width, self.height = resolution
        self.fps = fps or config.DEFAULT_FPS
        
        logger.info(f"FrameGenerator: {self.width}x{self.height} @ {self.fps}fps")
    
    def load_and_resize_image(self, image_path: str) -> np.ndarray:
        """
        Load image and resize to fit resolution
        
        Returns:
            RGB numpy array
        """
        try:
            img = Image.open(image_path).convert('RGB')
            
            # Resize to fit height
            img = img.resize(
                (int(img.width * self.height / img.height), self.height),
                Image.Resampling.LANCZOS
            )
            
            # If width < target, resize to width
            if img.width < self.width:
                img = img.resize(
                    (self.width, int(img.height * self.width / img.width)),
                    Image.Resampling.LANCZOS
                )
            
            return np.array(img, dtype=np.uint8)
            
        except Exception as e:
            logger.error(f"Failed to load image: {e}")
            raise
    
    def create_black_background(self) -> np.ndarray:
        """Create black background frame"""
        return np.zeros((self.height, self.width, 3), dtype=np.uint8)
    
    def composite_image_centered(
        self, 
        background: np.ndarray, 
        image: np.ndarray
    ) -> np.ndarray:
        """
        Composite image on background (centered)
        
        Args:
            background: Background frame
            image: Image to composite
            
        Returns:
            Composited frame
        """
        img_h, img_w = image.shape[:2]
        
        # If image is too large, crop it
        if img_h > self.height:
            start_y = (img_h - self.height) // 2
            image = image[start_y:start_y + self.height, :, :]
            img_h = self.height
        
        if img_w > self.width:
            start_x = (img_w - self.width) // 2
            image = image[:, start_x:start_x + self.width, :]
            img_w = self.width
        
        # Calculate centered position
        x = (self.width - img_w) // 2
        y = (self.height - img_h) // 2
        
        # Composite
        result = background.copy()
        
        try:
            result[y:y+img_h, x:x+img_w] = image
        except ValueError as e:
            logger.error(f"Composite error: bg={result.shape}, img={image.shape}, pos=({y}:{y+img_h}, {x}:{x+img_w})")
            raise
        
        return result
    
    def apply_ken_burns_to_frame(
        self,
        image: np.ndarray,
        trajectory_state: Dict,
        direction: str
    ) -> np.ndarray:
        """
        Apply Ken Burns effect to single frame
        
        Args:
            image: Original image
            trajectory_state: Pre-calculated state (zoom, pan_x_factor, pan_y_factor)
            direction: Ken Burns direction
            
        Returns:
            Transformed frame
        """
        zoom = trajectory_state['zoom']
        
        # Resize with zoom
        zoomed = resize_frame_numpy(image, zoom)
        zoomed_h, zoomed_w = zoomed.shape[:2]
        
        # Calculate crop offsets
        if direction in ["pan_left", "pan_right"]:
            max_x = max(0, zoomed_w - self.width)
            x_offset = int(max_x * (0.5 + trajectory_state['pan_x_factor']))
            y_offset = (zoomed_h - self.height) // 2
        else:
            x_offset = (zoomed_w - self.width) // 2
            y_offset = (zoomed_h - self.height) // 2
        
        # Clamp offsets
        x_offset = max(0, min(x_offset, max(0, zoomed_w - self.width)))
        y_offset = max(0, min(y_offset, max(0, zoomed_h - self.height)))
        
        # Calculate end points
        x_end = min(x_offset + self.width, zoomed_w)
        y_end = min(y_offset + self.height, zoomed_h)
        
        # Crop
        cropped = zoomed[y_offset:y_end, x_offset:x_end]
        
        # If cropped is smaller than target (edge case), pad it
        if cropped.shape[0] < self.height or cropped.shape[1] < self.width:
            padded = np.zeros((self.height, self.width, 3), dtype=np.uint8)
            padded[:cropped.shape[0], :cropped.shape[1]] = cropped
            return padded
        
        return cropped
    
    def overlay_subtitle(
        self,
        frame: np.ndarray,
        word_image: np.ndarray,
        position: Tuple[int, int]
    ) -> np.ndarray:
        """
        Overlay subtitle word on frame
        
        Args:
            frame: Background frame
            word_image: RGBA word image
            position: (x, y) position
            
        Returns:
            Frame with subtitle
        """
        x, y = position
        word_h, word_w = word_image.shape[:2]
        
        # Clip to frame bounds
        if x < 0 or y < 0 or x + word_w > self.width or y + word_h > self.height:
            return frame
        
        # Alpha blending
        alpha = word_image[:, :, 3:4] / 255.0
        rgb = word_image[:, :, :3]
        
        frame_region = frame[y:y+word_h, x:x+word_w]
        blended = (rgb * alpha + frame_region * (1 - alpha)).astype(np.uint8)
        
        result = frame.copy()
        result[y:y+word_h, x:x+word_w] = blended
        
        return result
    
    def generate_slide_frames(
        self,
        slide: Slide,
        kb_params: Dict,
        kb_trajectory: List[Dict],
        words_data: List[Dict],
        word_cache: Dict,
        slide_start_time: float
    ) -> Generator[np.ndarray, None, None]:
        """
        Generate frames for single slide with all effects
        
        Args:
            slide: Slide object
            kb_params: Ken Burns parameters
            kb_trajectory: Pre-calculated Ken Burns trajectory
            words_data: Word timing data
            word_cache: Pre-rendered word images
            slide_start_time: Slide start time in video
            
        Yields:
            RGB frames
        """
        # Load image
        image = self.load_and_resize_image(slide.image_path)
        
        # Calculate frame count
        num_frames = int(slide.duration * self.fps)
        
        # Pre-calculate subtitle positions
        word_positions = {}
        for word_data in words_data:
            word = word_data['word'].strip()
            if word in word_cache:
                word_img, _ = word_cache[word]
                # Center horizontally, vertically
                x = (self.width - word_img.shape[1]) // 2
                y = (self.height - word_img.shape[0]) // 2
                word_positions[word] = (x, y)
        
        # Generate frames
        for frame_idx in range(num_frames):
            # Current time in slide
            t = frame_idx / self.fps
            absolute_t = slide_start_time + t
            
            # Apply Ken Burns
            trajectory_idx = min(frame_idx, len(kb_trajectory) - 1)
            frame = self.apply_ken_burns_to_frame(
                image,
                kb_trajectory[trajectory_idx],
                kb_params['direction']
            )
            
            # Composite on black background
            background = self.create_black_background()
            frame = self.composite_image_centered(background, frame)
            
            # Apply subtitle
            for word_data in words_data:
                word = word_data['word'].strip()
                word_start = word_data['start']
                word_end = word_data['end']
                
                # Check if word should be visible
                if word_start <= absolute_t <= word_end and word in word_cache:
                    word_img, _ = word_cache[word]
                    pos = word_positions.get(word)
                    
                    if pos:
                        frame = self.overlay_subtitle(frame, word_img, pos)
            
            # Final validation
            if frame.shape != (self.height, self.width, 3):
                logger.error(f"Invalid frame shape: {frame.shape}, expected ({self.height}, {self.width}, 3)")
                logger.error(f"Frame {frame_idx}/{num_frames} of slide")
                # Resize/crop to correct size
                if frame.shape[0] != self.height or frame.shape[1] != self.width:
                    from PIL import Image
                    frame_pil = Image.fromarray(frame)
                    frame_pil = frame_pil.resize((self.width, self.height), Image.Resampling.LANCZOS)
                    frame = np.array(frame_pil)
            
            if frame.dtype != np.uint8:
                frame = frame.astype(np.uint8)
            
            yield frame
    
    def generate_transition_frames(
        self,
        prev_slide_frames: List[np.ndarray],
        next_slide_frames: List[np.ndarray],
        transition_type: str,
        transition_duration: float
    ) -> Generator[np.ndarray, None, None]:
        """
        Generate transition frames between slides
        
        Args:
            prev_slide_frames: Last frames from previous slide
            next_slide_frames: First frames from next slide
            transition_type: 'glitch', 'flash', or 'zoom_punch'
            transition_duration: Transition duration in seconds
            
        Yields:
            Transition frames
        """
        num_transition_frames = int(transition_duration * self.fps)
        
        # Ensure we have enough frames
        if len(prev_slide_frames) < num_transition_frames:
            logger.warning("Not enough prev frames for transition")
            return
        
        if len(next_slide_frames) < num_transition_frames:
            logger.warning("Not enough next frames for transition")
            return
        
        # Apply transition to both sides
        for i in range(num_transition_frames):
            progress = i / max(num_transition_frames - 1, 1)
            
            prev_frame = prev_slide_frames[-(num_transition_frames - i)]
            
            if transition_type == "glitch":
                # Glitch previous frame
                frame = apply_glitch_frame(prev_frame, progress, i, self.fps)
            elif transition_type == "flash":
                # Flash previous frame
                frame = apply_flash_frame(prev_frame, progress, fade_out=True)
            elif transition_type == "zoom_punch":
                # Zoom previous frame
                frame = apply_zoom_punch_frame(prev_frame, progress)
            else:
                frame = prev_frame
            
            yield frame
        
        # Now apply transition to next slide frames
        for i in range(num_transition_frames):
            progress = i / max(num_transition_frames - 1, 1)
            
            next_frame = next_slide_frames[i]
            
            if transition_type == "glitch":
                frame = apply_glitch_frame(next_frame, progress, i, self.fps, fade_in=True)
            elif transition_type == "flash":
                frame = apply_flash_frame(next_frame, 1 - progress, fade_out=False)
            else:
                frame = next_frame
            
            yield frame