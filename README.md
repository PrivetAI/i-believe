# 🎬 AI Video Generator

Local Streamlit application for building short-form videos from manually prepared slides. Each slide combines your text and imagery, and the app produces a voiced video with word-level subtitles, Ken Burns motion, and smooth transitions.

## Highlights
- Manual slide builder with unlimited slides (text + image per slide)
- Edge TTS integration with on-demand language/voice loading and per-slide audio caching
- Word-by-word subtitles rendered at the center of the frame (white text with black outline)
- Ken Burns zoom/pan motion plus crossfade transitions between slides
- Automatic cleanup of intermediate cache files after a successful render
- Built-in log viewer and persistent volumes for generated videos, cache, and Whisper models

## Project Layout
```
video2/
├── app/
│   ├── main.py                 # Streamlit UI and end-to-end workflow
│   ├── config.py               # Runtime configuration
│   ├── models/
│   │   └── slide.py            # Slide dataclass
│   ├── services/
│   │   ├── tts_service.py      # Microsoft Edge TTS integration
│   │   ├── whisper_service.py  # Faster-Whisper wrapper for word timestamps
│   │   └── video_service.py    # Slide assembly, effects, and export
│   └── utils/
│       ├── ken_burns.py        # Ken Burns parameters and application
│       ├── subtitle_renderer.py # Centered single-word subtitle renderer
│       ├── transitions.py      # Crossfade transitions between clips
│       └── logger.py           # Logger setup and helpers
├── cache/                      # Ephemeral files (images, audio, whisper temp)
├── logs/                       # Application logs
├── output/                     # Final MP4 renders
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── specification.md
```

## Setup

### Prerequisites
- Docker and Docker Compose (recommended path)
- At least 8 GB RAM and a modern CPU (Whisper runs on CPU)
- Stable internet connection for Edge TTS voice list and first Whisper model download

### Run with Docker Compose
```bash
git clone <repository-url>
cd video2
docker-compose up --build
```

Open `http://localhost:8501` in your browser. The compose file mounts `./output`, `./cache`, and `./logs` so the files stay on the host, and keeps the Whisper model cache in a named volume (`whisper-cache`).

### Run locally without Docker
1. Install system dependencies (example for Ubuntu/Debian):
   ```bash
   sudo apt-get update
   sudo apt-get install ffmpeg imagemagick libsm6 libxext6 libxrender-dev
   ```
   Install the Montserrat font (or place `Montserrat-Bold.ttf` alongside the app) for subtitle rendering quality.
2. Install Python requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the Streamlit app:
   ```bash
   streamlit run app/main.py
   ```

## Workflow
1. **Launch the app.** The sidebar loads available Edge TTS languages on first render. If it fails, check your internet connection and rerun.
2. **Pick a voice.** Choose a language, press `Load Voices`, and select a voice from the dropdown. A voice is required before you can start rendering.
3. **Configure resolution.** Choose between vertical `9:16 (1080x1920)` and horizontal `16:9 (1920x1080)` output.
4. **Add slides.**
   - Enter the narration text for the slide.
   - Upload an image (`.jpg`, `.jpeg`, `.png`, up to 10 MB).
   - Click `➕ Add Slide`. The image is copied to `cache/<generation_id>/images`.
5. **Manage the slide list.** Expand slides to preview text and imagery, delete individual slides, or clear the whole list to start over.
6. **Generate the video.** Click `🎬 Generate Video` (enabled once a voice is selected). The app runs four sequential steps with a progress bar:
   - text-to-speech audio synthesis per slide,
   - Whisper transcription for word-level timestamps,
   - video assembly with Ken Burns and crossfades,
   - final MP4 export to `output/video_<uuid>.mp4`.
7. **Review the result.** The video appears in the UI for playback and download. File size and resolution are shown next to the download button.
8. **Check logs if needed.** Expand the "📋 View Logs" panel or inspect `logs/app.log` on disk for the last 100 lines of context.
9. **Cleanup.** On success, intermediate artifacts in `cache/<generation_id>` are deleted automatically (`CACHE_AUTO_CLEANUP = True`). Failed runs keep the cache for inspection.

## Configuration
Key options live in `app/config.py`:

```python
# Video output
VIDEO_RESOLUTIONS = {
    "9:16 (TikTok/Reels)": (1080, 1920),
    "16:9 (YouTube)": (1920, 1080),
}
DEFAULT_FPS = 30
DEFAULT_CODEC = "libx264"
DEFAULT_AUDIO_CODEC = "aac"
CRF = 23
MIN_SLIDE_DURATION = 5.0

# Ken Burns motion
KEN_BURNS_ZOOM_RANGE = (1.0, 1.5)
KEN_BURNS_PAN_RANGE = (0.1, 0.2)
KEN_BURNS_DIRECTIONS = [
    "zoom_in", "zoom_out",
    "pan_left", "pan_right", "pan_up", "pan_down",
]

# Transitions (currently rendered as crossfades)
TRANSITION_DURATION = 0.5

# Subtitle styling
SUBTITLE_FONT = "Montserrat-Bold"
SUBTITLE_FONT_SIZE = 70
SUBTITLE_COLOR = "white"
SUBTITLE_OUTLINE_COLOR = "black"
SUBTITLE_OUTLINE_WIDTH = 5
SUBTITLE_LINE_SPACING = 0.4
SUBTITLE_POSITION = "center"

# Whisper + cache
WHISPER_MODEL = "small"
CACHE_AUTO_CLEANUP = True
ALLOWED_IMAGE_EXTENSIONS = ["jpg", "jpeg", "png"]
MAX_IMAGE_SIZE_MB = 10
```

Adjust these values to tune output quality, subtitle look, or supported upload formats. Remember to rebuild the Docker image after changes if you are running inside a container.

## Troubleshooting
- **Cannot load languages/voices** - Ensure outbound internet access. Edge TTS requires it to list voices. Retry after network is restored.
- **Whisper download takes a long time** - The first transcription downloads the `small` model into the `whisper-cache` volume. Subsequent runs reuse it.
- **Video generation fails** - Review `logs/app.log` and confirm uploaded images are valid and under the size limit. Check available RAM (8 GB recommended).
- **Subtitles look jagged** - Install the Montserrat font on the host (if running outside Docker) so `subtitle_renderer.py` can load it.
- **Transitions look the same** - The current implementation applies crossfade-style transitions even though additional types are listed. Customize `utils/transitions.py` if you need more effects.

## Logs
Logs are written to `logs/app.log` and surfaced inside the UI (`📋 View Logs`). Each major step in the pipeline is recorded with timestamps:
```
[2025-01-15 14:23:45] [INFO] [video_service] Assembling video with 4 slides
[2025-01-15 14:23:46] [INFO] [subtitle_renderer] Rendering 128 word-by-word subtitles
```

## Roadmap
- ⏳ AI-assisted script/image generation workflow (OpenAI + SDXL)
- ⏳ Background music and SFX layer
- ⏳ Custom subtitle themes and font uploads
- ⏳ Batch rendering queue
- ⏳ Direct publishing integrations

## License

MIT License - enjoy, modify, and ship your own videos.
