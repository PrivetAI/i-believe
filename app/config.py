"""Configuration settings"""

# Video settings
VIDEO_RESOLUTIONS = {
    "9:16 (TikTok/Reels)": (1080, 1920),
    "16:9 (YouTube)": (1920, 1080)
}
DEFAULT_FPS = 20
CRF = 26
MOVIEPY_PRESET = 'veryfast'

# Ken Burns settings
ENABLE_KEN_BURNS = True  # Set to False for maximum speed
KEN_BURNS_ZOOM_RANGE = (1.0, 1.3)
KEN_BURNS_PAN_RANGE = (0.05, 0.15)
KEN_BURNS_DIRECTIONS = ["zoom_in", "zoom_out", "pan_left", "pan_right"]

# Transition settings
TRANSITION_DURATION = 0.3  # Duration in seconds

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