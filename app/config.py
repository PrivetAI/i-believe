"""
Configuration settings - Maximum optimization for i5 8-core 8GB RAM
"""

# Video settings - Optimized
VIDEO_RESOLUTIONS = {
    "9:16 (TikTok/Reels)": (1080, 1920),
    "16:9 (YouTube)": (1920, 1080)
}
DEFAULT_FPS = 20  # Reduced from 24 (16% fewer frames)
DEFAULT_CODEC = "h264_qsv"  # Intel GPU encoding (fallback to libx264)
DEFAULT_AUDIO_CODEC = "aac"
CRF = 26  # Slightly higher for faster encoding (was 23)

# Ken Burns settings - Optimized
KEN_BURNS_ZOOM_RANGE = (1.0, 1.3)  # Reduced max zoom (was 1.5)
KEN_BURNS_PAN_RANGE = (0.05, 0.15)  # Reduced pan range
KEN_BURNS_DIRECTIONS = ["zoom_in", "zoom_out", "pan_left", "pan_right"]  # Removed up/down
KEN_BURNS_CACHE_FRAMES = True  # Enable frame caching
KEN_BURNS_INTERPOLATION_STEPS = 10  # Pre-calculate key frames

# Transition settings
TRANSITION_DURATION = 0.4  # Slightly faster (was 0.5)
TRANSITION_TYPES = ["glitch", "flash", "zoom_punch"]

# Subtitle settings - Optimized word-by-word
SUBTITLE_FONT = "Montserrat-Bold"
SUBTITLE_FONT_SIZE = 70
SUBTITLE_COLOR = "white"
SUBTITLE_OUTLINE_COLOR = "black"
SUBTITLE_OUTLINE_WIDTH = 5
SUBTITLE_POSITION = "center"
SUBTITLE_WORD_CACHE = True  # Enable aggressive word caching

# Cache settings
MIN_SLIDE_DURATION = 5.0
CACHE_AUTO_CLEANUP = True

# Whisper settings
WHISPER_MODEL = "small"

# API settings
API_TIMEOUT = 60

# File upload settings
ALLOWED_IMAGE_EXTENSIONS = ["jpg", "jpeg", "png"]
MAX_IMAGE_SIZE_MB = 10

# Performance settings - MAXIMUM OPTIMIZATION
MOVIEPY_THREADS = 6  # Increased from 4 (use more cores)
MOVIEPY_PRESET = 'veryfast'  # Better than ultrafast for size/speed
ENABLE_PROGRESS_BAR = False
GC_COLLECT_AFTER_SLIDE = True
GC_COLLECT_INTERVAL = 2  # Force GC every 2 slides

# GPU Encoding settings
GPU_ENCODING_ENABLED = True
GPU_FALLBACK_TO_CPU = True  # Auto fallback if GPU fails

# Image processing optimization
IMAGE_RESIZE_QUALITY = 85  # JPEG quality for intermediate steps
USE_FAST_INTERPOLATION = True  # Use faster scipy interpolation

# Memory optimization
MAX_CONCURRENT_CLIPS = 3  # Process max 3 clips in memory
CLEAR_CLIP_CACHE_AGGRESSIVE = True