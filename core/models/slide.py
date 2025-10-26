"""
Data models for slides and video
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Slide:
    """
    Represents a single slide in the video
    """
    text: str
    image_path: str
    audio_path: Optional[str] = None
    duration: Optional[float] = None
    
    def __post_init__(self):
        if not self.text or not self.text.strip():
            raise ValueError("Slide text cannot be empty")
        if not self.image_path:
            raise ValueError("Slide image path cannot be empty")