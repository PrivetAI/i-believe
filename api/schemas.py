"""
Pydantic schemas for API requests and responses
"""
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Literal


class SlideInput(BaseModel):
    """Single slide input"""
    text: str = Field(..., min_length=1, description="Slide narration text")
    image_path: Optional[str] = Field(None, description="Local image path for manual mode")
    image_url: Optional[HttpUrl] = Field(None, description="Image URL for external mode")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "Welcome to our presentation",
                "image_path": "/cache/abc123/images/slide1.jpg"
            }
        }


class GenerateVideoRequest(BaseModel):
    """Request for video generation"""
    slides: List[SlideInput] = Field(..., min_items=1, max_items=50)
    voice: str = Field(..., description="Edge TTS voice identifier")
    resolution: str = Field(default="9:16", description="Video resolution: 9:16 or 16:9")
    
    class Config:
        json_schema_extra = {
            "example": {
                "slides": [
                    {
                        "text": "Welcome to our presentation",
                        "image_path": "/cache/abc123/images/slide1.jpg"
                    }
                ],
                "voice": "en-US-AriaNeural",
                "resolution": "9:16"
            }
        }


class VoiceInfo(BaseModel):
    """Voice information"""
    short_name: str
    gender: Optional[str] = None
    locale: str


class VideoResponse(BaseModel):
    """Response after video generation"""
    job_id: str
    status: Literal["queued", "processing", "completed", "failed"]
    video_path: Optional[str] = None
    video_url: Optional[str] = None
    file_size_mb: Optional[float] = None
    duration_seconds: Optional[float] = None
    error: Optional[str] = None


class JobStatusResponse(BaseModel):
    """Job status response"""
    job_id: str
    status: Literal["queued", "processing", "completed", "failed"]
    progress: Optional[float] = Field(None, ge=0, le=1, description="Progress 0-1")
    current_step: Optional[str] = None
    video_path: Optional[str] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None