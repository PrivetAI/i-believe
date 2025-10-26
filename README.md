# 🎬 AI Video Generator

**FastAPI + Streamlit** application for building short-form videos from manually prepared slides. Each slide combines text and imagery, producing a voiced video with word-level subtitles, Ken Burns motion, and dynamic transitions.

## 🏗️ Architecture

The project is split into **two isolated layers**:

### 1. **Backend API** (`api/` + `core/`)
- FastAPI REST API for video generation
- Isolated business logic (pipeline, services)
- Supports two modes:
  - **Manual mode**: Local images (current workflow)
  - **External mode**: Images from URLs (for future AI integration)
- Background job processing with progress tracking

### 2. **Frontend UI** (`ui/`)
- Streamlit interface for manual slide creation
- Communicates with backend via HTTP API
- Real-time job status polling

This architecture allows **complete isolation** for future AI content generation module.

---

## ✨ Features

- **Manual slide builder** with unlimited slides (text + image per slide)
- **Edge TTS integration** with on-demand language/voice loading and per-slide audio caching
- **Word-by-word subtitles** rendered at center with smooth fade effects
- **Ken Burns motion** (zoom/pan) on each slide
- **Dynamic transitions** between slides:
  - Glitch effect (CapCut-style RGB shift + noise)
  - Flash transition (white flash)
  - Zoom punch (explosive zoom with shake)
- **Background job processing** with progress tracking
- **REST API** for integration with external systems
- **Automatic cleanup** of intermediate cache files after successful render
- **Built-in log viewer** and persistent volumes

---

## 📁 Project Structure

```
video-generator/
├── api/                              # FastAPI Backend
│   ├── main.py                       # FastAPI application
│   ├── routes.py                     # API endpoints
│   └── schemas.py                    # Pydantic models
│
├── core/                             # Business Logic (isolated)
│   ├── pipeline.py                   # Video generation pipeline
│   ├── services/
│   │   ├── tts_service.py            # Edge TTS integration
│   │   ├── whisper_service.py        # Faster-Whisper timestamps
│   │   └── video_service.py          # FFmpeg video assembly
│   ├── models/
│   │   └── slide.py                  # Slide dataclass
│   └── utils/
│       ├── effects.py                # Ken Burns + Transitions + Subtitles
│       └── logger.py                 # Logger setup
│
├── ui/                               # Streamlit Frontend
│   └── app.py                        # Streamlit interface (API client)
│
├── cache/                            # Temporary files (ephemeral)
├── logs/                             # Application logs
├── output/                           # Final MP4 renders
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── config.py                         # Configuration
```

---

## 🚀 Setup

### Prerequisites
- Docker and Docker Compose (recommended)
- At least 8 GB RAM and modern CPU
- Internet connection for Edge TTS and Whisper model download

### Quick Start with Docker Compose

```bash
git clone <repository-url>
cd video-generator
docker-compose up --build
```

**Services:**
- API: `http://localhost:8000` (Swagger docs at `/docs`)
- UI: `http://localhost:8501`

Volumes are mounted for `./output`, `./cache`, and `./logs`.

### Local Setup (without Docker)

1. **Install system dependencies** (Ubuntu/Debian):
   ```bash
   sudo apt-get update
   sudo apt-get install ffmpeg imagemagick libsm6 libxext6 libxrender-dev
   ```

2. **Install Python requirements**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Start Backend API**:
   ```bash
   cd api
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

4. **Start Frontend UI** (in another terminal):
   ```bash
   cd ui
   streamlit run app.py --server.port 8501
   ```

---

## 🎯 Workflow

### Manual Mode (Current)

1. **Open UI** at `http://localhost:8501`
2. **Select voice**:
   - Choose language → Click "Load Voices" → Select voice
3. **Configure resolution**: Vertical `9:16` or Horizontal `16:9`
4. **Add slides**:
   - Enter narration text
   - Upload image (JPG/PNG, up to 10 MB)
   - Click "➕ Add Slide"
5. **Generate video**:
   - Click "🎬 Generate Video"
   - Monitor progress in real-time
6. **Download**: Video appears for playback and download

### API Mode (for External Integration)

```bash
# Submit job
curl -X POST http://localhost:8000/api/v1/external/generate \
  -H "Content-Type: application/json" \
  -d '{
    "slides": [
      {
        "text": "Welcome to our video",
        "image_url": "http://example.com/image1.jpg"
      }
    ],
    "voice": "en-US-AriaNeural",
    "resolution": "9:16"
  }'

# Response: {"job_id": "abc123", "status": "queued"}

# Poll status
curl http://localhost:8000/api/v1/status/abc123

# Download video
curl -O http://localhost:8000/api/v1/download/abc123
```

---

## ⚙️ Configuration

Edit `config.py`:

```python
# Video output
VIDEO_RESOLUTIONS = {
    "9:16 (TikTok/Reels)": (1080, 1920),
    "16:9 (YouTube)": (1920, 1080),
}
DEFAULT_FPS = 20
CRF = 23  # Lower = better quality (18-28)
MOVIEPY_PRESET = 'medium'  # veryfast/fast/medium/slow

# Ken Burns motion
ENABLE_KEN_BURNS = True
KEN_BURNS_ZOOM_RANGE = (1.0, 1.15)
KEN_BURNS_PAN_RANGE = (0.03, 0.08)

# Transitions
TRANSITION_DURATION = 0.3  # seconds

# Subtitles
SUBTITLE_FONT_SIZE = 70

# Whisper
WHISPER_MODEL = "small"  # tiny/base/small/medium/large

# Cache
CACHE_AUTO_CLEANUP = True
```

---

## 🔌 API Endpoints

### Video Generation

**POST** `/api/v1/manual/generate` - Generate from local images
**POST** `/api/v1/external/generate` - Generate from URLs (for AI integration)

**Request Body**:
```json
{
  "slides": [
    {
      "text": "Slide narration",
      "image_path": "/cache/xxx/img1.jpg"  // manual mode
      // OR
      "image_url": "http://..."             // external mode
    }
  ],
  "voice": "en-US-AriaNeural",
  "resolution": "9:16"
}
```

**Response**:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued"
}
```

### Job Management

**GET** `/api/v1/status/{job_id}` - Get job status and progress

**Response**:
```json
{
  "job_id": "...",
  "status": "processing",  // queued|processing|completed|failed
  "progress": 0.65,
  "current_step": "Assembling video...",
  "video_path": null
}
```

**GET** `/api/v1/download/{job_id}` - Download completed video

### Voice Management

**GET** `/api/v1/languages` - List available languages
**GET** `/api/v1/voices?language=en-US` - List voices for language

---

## 🐛 Troubleshooting

**Cannot load languages/voices**
- Ensure internet connection (Edge TTS requires it)
- Check API logs: `logs/api.log`

**Whisper download takes long**
- First run downloads `small` model (~500MB)
- Uses `whisper-cache` Docker volume for persistence

**Video generation fails**
- Check `logs/api.log` for errors
- Verify uploaded images are valid and under 10MB
- Ensure 8GB+ RAM available

**Transitions look same**
- Transitions are randomized each time
- Check `TRANSITION_DURATION` in `config.py`

---

## 📊 Logs

Logs are written to:
- API: `logs/api.log`
- UI: `logs/ui.log`

View in UI via "📋 View Logs" panel or check files directly.

---

## 🗺️ Roadmap

- ✅ FastAPI backend with job queue
- ✅ Manual mode with local uploads
- ✅ External mode for AI integration
- ⏳ Redis/Celery for production job queue
- ⏳ AI content generator (separate project)
- ⏳ Background music and SFX
- ⏳ Custom subtitle themes
- ⏳ Batch rendering

---

## 📝 License

MIT License - build, modify, and ship your own videos.