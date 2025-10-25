"""
Configuration settings - Optimized for low-end CPU
"""

# Video settings - Optimized for i5 8-core 8GB RAM
VIDEO_RESOLUTIONS = {
    "9:16 (TikTok/Reels)": (1080, 1920),
    "16:9 (YouTube)": (1920, 1080)
}
DEFAULT_FPS = 24  # Reduced from 30 for faster render
DEFAULT_CODEC = "libx264"
DEFAULT_AUDIO_CODEC = "aac"
CRF = 23

# Ken Burns settings
KEN_BURNS_ZOOM_RANGE = (1.0, 1.5)
KEN_BURNS_PAN_RANGE = (0.1, 0.2)
KEN_BURNS_DIRECTIONS = ["zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up", "pan_down"]

# Transition settings
TRANSITION_DURATION = 0.5
TRANSITION_TYPES = ["glitch", "spin_blur", "flash", "zoom_punch"]

# Subtitle settings - White centered style
SUBTITLE_FONT = "Montserrat-Bold"
SUBTITLE_FONT_SIZE = 70
SUBTITLE_COLOR = "white"
SUBTITLE_OUTLINE_COLOR = "black"
SUBTITLE_OUTLINE_WIDTH = 5
SUBTITLE_POSITION = "center"

# Cache settings
MIN_SLIDE_DURATION = 5.0
CACHE_AUTO_CLEANUP = True

# Whisper settings
WHISPER_MODEL = "small"  # Keep as requested (can use "medium" for better accuracy)

# API settings
API_TIMEOUT = 60

# File upload settings
ALLOWED_IMAGE_EXTENSIONS = ["jpg", "jpeg", "png"]
MAX_IMAGE_SIZE_MB = 10

# Performance settings for low-end CPU
MOVIEPY_THREADS = 4
MOVIEPY_PRESET = 'veryfast'  # veryfast, faster, fast, medium, slow, slower, veryslow
ENABLE_PROGRESS_BAR = False  # Disable to reduce overhead
GC_COLLECT_AFTER_SLIDE = True  # Force garbage collection after each slide