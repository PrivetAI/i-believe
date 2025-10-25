"""Configuration settings"""
import random

# Initialize random seed for transitions
random.seed()

# Video settings
VIDEO_RESOLUTIONS = {
    "9:16 (TikTok/Reels)": (1080, 1920),
    "16:9 (YouTube)": (1920, 1080)
}
DEFAULT_FPS = 20
CRF = 23  # Lower = better quality (18-28 range)
MOVIEPY_PRESET = 'medium'  # veryfast/fast/medium/slow

# Ken Burns settings
ENABLE_KEN_BURNS = True
KEN_BURNS_ZOOM_RANGE = (1.0, 1.15)  # Very smooth range
KEN_BURNS_PAN_RANGE = (0.03, 0.08)  # Very smooth pan
KEN_BURNS_DIRECTIONS = ["zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up", "pan_down"]

# Transition settings
TRANSITION_DURATION = 0.3

# Subtitle settings
SUBTITLE_FONT_SIZE = 70

# Cache settings
MIN_SLIDE_DURATION = 5.0
CACHE_AUTO_CLEANUP = True

# Whisper settings
WHISPER_MODEL = "small"

# File upload settings
ALLOWED_IMAGE_EXTENSIONS = ["jpg", "jpeg", "png"]
MAX_IMAGE_SIZE_MB = 10