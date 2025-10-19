"""
Configuration settings for AI Video Generator
"""

# Video settings
VIDEO_RESOLUTIONS = {
    "9:16 (TikTok/Reels)": (1080, 1920),
    "16:9 (YouTube)": (1920, 1080)
}
DEFAULT_FPS = 30
DEFAULT_CODEC = "libx264"
DEFAULT_AUDIO_CODEC = "aac"
CRF = 23

# Ken Burns settings
KEN_BURNS_ZOOM_RANGE = (1.1, 1.3)
KEN_BURNS_PAN_RANGE = (0.05, 0.10)  # 5-10% of dimension
KEN_BURNS_DIRECTIONS = ["zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up", "pan_down"]

# Transition settings
TRANSITION_DURATION = 0.5
TRANSITION_TYPES = ["fade", "crossfade", "wipe_left", "wipe_right", "wipe_up", "wipe_down", "dissolve"]

# Subtitle settings - Word-by-word live captions
SUBTITLE_FONT = "Arial-Bold"  # System font fallback
SUBTITLE_FONT_SIZE = 60
SUBTITLE_COLOR = "yellow"
SUBTITLE_OUTLINE_COLOR = "black"
SUBTITLE_OUTLINE_WIDTH = 3
SUBTITLE_POSITION = ("center", 0.8)  # (x, y) relative to frame
SUBTITLE_HIGHLIGHT_COLOR = "white"
SUBTITLE_HIGHLIGHT_SIZE = 70

# Attention effects settings
EFFECTS_PROBABILITY = 0.3  # 30% chance per slide
EFFECT_TYPES = ["zoom_punch", "flash", "shake"]

# Cache settings
MIN_SLIDE_DURATION = 5.0  # seconds
CACHE_AUTO_CLEANUP = True

# Whisper settings
WHISPER_MODEL = "medium"

# API settings
API_TIMEOUT = 60  # seconds

# File upload settings
ALLOWED_IMAGE_EXTENSIONS = ["jpg", "jpeg", "png"]
MAX_IMAGE_SIZE_MB = 10