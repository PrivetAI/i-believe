# 🎬 AI Video Generator

A local application for automated generation of short-form videos with AI-powered voiceover, synchronized word-by-word subtitles, and cinematic effects.

## ✨ Features

- **Manual Content Upload**: Create videos by uploading your own images and text
- **Text-to-Speech**: High-quality voiceover using Edge TTS with 100+ voices
- **Live Captions**: Word-by-word subtitles synchronized with speech (TikTok/CapCut style)
- **Ken Burns Effects**: Automatic zoom and pan effects on images
- **Smart Transitions**: Random transitions between slides (crossfade, wipe, dissolve)
- **Multiple Formats**: Support for 9:16 (TikTok/Reels) and 16:9 (YouTube) formats

## 🏗️ Architecture

```
ai-video-generator/
├── app/
│   ├── main.py                 # Streamlit application
│   ├── config.py               # Configuration settings
│   ├── services/
│   │   ├── tts_service.py      # Edge TTS integration
│   │   ├── whisper_service.py  # Speech-to-text with timestamps
│   │   └── video_service.py    # Video assembly with MoviePy
│   ├── utils/
│   │   ├── ken_burns.py        # Ken Burns effect
│   │   ├── subtitle_renderer.py # Subtitle overlay
│   │   ├── transitions.py      # Video transitions
│   │   └── logger.py           # Logging system
│   └── models/
│       └── slide.py            # Data models
├── output/                     # Generated videos
├── cache/                      # Temporary files (auto-cleanup)
├── logs/                       # Application logs
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

### Technology Stack

- **Backend**: Python 3.11+
- **Framework**: Streamlit
- **Video Processing**: MoviePy
- **TTS**: Edge TTS
- **Speech Recognition**: Faster-Whisper
- **Deployment**: Docker + Docker Compose

## 🚀 Installation

### Prerequisites

- Docker and Docker Compose installed
- Minimum 8GB RAM
- Intel i5 CPU or equivalent (no GPU required)

### Quick Start

1. **Clone the repository**
```bash
git clone <repository-url>
cd ai-video-generator
```

2. **Build and run with Docker Compose**
```bash
docker-compose up --build
```

3. **Access the application**
Open your browser and navigate to: `http://localhost:8501`

### Manual Installation (without Docker)

1. **Install system dependencies**
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg
```

2. **Install Python dependencies**
```bash
pip install -r requirements.txt
```

3. **Run the application**
```bash
streamlit run app/main.py
```

## 📖 Usage Guide

### Manual Upload Mode

1. **Select Voice Settings** (Sidebar)
   - Choose your preferred language
   - Click "Load Voices"
   - Select a voice from the dropdown

2. **Configure Video Settings** (Sidebar)
   - Choose resolution (9:16 for TikTok/Reels or 16:9 for YouTube)

3. **Create Slides** (Main Area)
   - Enter text for the slide in the text area
   - Upload an image (JPG/PNG)
   - Click "➕ Add Slide"
   - Repeat for multiple slides

4. **Review Slides**
   - Expand any slide to review content
   - Delete slides if needed
   - Use "Clear All" to start over

5. **Generate Video**
   - Click "🎬 Generate Video"
   - Wait for processing (1-3 minutes for 30-60 second video)
   - Download the generated video

### Generation Process

The application follows these steps:

1. **Text-to-Speech Generation**: Converts slide text to audio using Edge TTS
2. **Word-Level Timestamps**: Extracts precise timing for each word using Whisper
3. **Video Assembly**: Creates video with Ken Burns effects and transitions
4. **Subtitle Rendering**: Adds word-by-word live captions
5. **Final Encoding**: Exports high-quality MP4 video

## ⚙️ Configuration

Edit `app/config.py` to customize:

### Video Settings
```python
VIDEO_RESOLUTIONS = {
    "9:16 (TikTok/Reels)": (1080, 1920),
    "16:9 (YouTube)": (1920, 1080)
}
DEFAULT_FPS = 30
```

### Ken Burns Effect
```python
KEN_BURNS_ZOOM_RANGE = (1.1, 1.3)  # Min/max zoom level
KEN_BURNS_PAN_RANGE = (0.05, 0.10)  # Pan distance (5-10%)
```

### Subtitles
```python
SUBTITLE_FONT_SIZE = 60
SUBTITLE_COLOR = "yellow"
SUBTITLE_HIGHLIGHT_COLOR = "white"
SUBTITLE_POSITION = ("center", 0.8)  # Bottom-center
```

### Transitions
```python
TRANSITION_DURATION = 0.5  # seconds
TRANSITION_TYPES = ["fade", "crossfade", "wipe_left", ...]
```

## 📊 Output Format

- **Video Codec**: H.264 (MP4)
- **Audio Codec**: AAC, 192 kbps
- **Frame Rate**: 30 FPS
- **Quality**: CRF 23 (balanced)

## 🔍 Troubleshooting

### Issue: "Failed to load voices"
**Solution**: Check your internet connection. Edge TTS requires internet to fetch voice list.

### Issue: Video generation fails
**Solutions**:
- Check logs in the "📋 View Logs" section
- Ensure images are valid JPG/PNG files
- Verify sufficient disk space in `output/` directory
- Check Docker container has enough memory (8GB minimum)

### Issue: Subtitles not appearing
**Solutions**:
- Verify Whisper model is properly loaded (check logs)
- Ensure audio is generated correctly
- Check subtitle configuration in `config.py`

### Issue: Poor video quality
**Solutions**:
- Adjust CRF value in `config.py` (lower = higher quality)
- Use higher resolution images
- Ensure images match target aspect ratio

## 📝 Logs

Application logs are available in:
- **File**: `logs/app.log`
- **UI**: Click "📋 View Logs" in the application
- **Docker**: `docker logs ai-video-generator`

Log format:
```
[2025-01-15 14:23:45] [INFO] [video_service] Starting video assembly...
[2025-01-15 14:23:46] [DEBUG] [ken_burns] Applying zoom 1.2x, pan right 8%
```

## 🛣️ Roadmap

Current MVP includes:
- ✅ Manual upload mode
- ✅ Edge TTS integration
- ✅ Word-by-word subtitles
- ✅ Ken Burns effects
- ✅ Video transitions
- ✅ Docker deployment

Future enhancements (not yet implemented):
- ⏳ AI-automated generation (GPT-4 + SDXL)
- ⏳ Background music support
- ⏳ Custom font upload
- ⏳ Attention effects (zoom punch, flash, shake)
- ⏳ Multiple subtitle styles
- ⏳ Batch video generation
- ⏳ Direct social media upload

## 🤝 Contributing

This is a self-contained MVP. For feature requests or bugs:
1. Check existing logs for errors
2. Review configuration in `config.py`
3. Submit detailed issue report

## 📄 License

MIT License - feel free to use and modify for your projects.

## 🙏 Acknowledgments

Built with:
- [Streamlit](https://streamlit.io/) - Web framework
- [MoviePy](https://zulko.github.io/moviepy/) - Video processing
- [Edge TTS](https://github.com/rany2/edge-tts) - Text-to-speech
- [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper) - Speech recognition

---

**Note**: This is an MVP (Minimum Viable Product) focused on manual upload mode. AI-automated generation features are planned for future releases.