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
- Intel GPU acceleration support (VAAPI)

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
- **Intel GPU acceleration** (VAAPI h264_vaapi encoder)
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
│       ├── ffmpeg_renderer.py        # Direct FFmpeg renderer (VAAPI)
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

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Intel GPU (optional, for hardware acceleration)
- At least 8 GB RAM and modern CPU
- Internet connection for Edge TTS and Whisper model download

### Start with Docker Compose

```bash
git clone <repository-url>
cd video-generator
docker-compose up --build
```

**Services:**
- API: `http://localhost:8000` (Swagger docs at `/docs`)
- UI: `http://localhost:8501`

Volumes are mounted for `./output`, `./cache`, and `./logs`.

### Verify GPU Acceleration (Intel only)

```bash
docker-compose exec api vainfo
```

Should show Intel GPU capabilities. If VAAPI is unavailable, system falls back to CPU encoding (libx264).

---

## 🎯 Workflow

### Manual Mode (Current)

1. **Open UI** at `http://localhost:8501`
2. **Select voice**:
   - Choose language → Click "Load Voices" → Select voice
3. **Configure resolution**: `9:16` (TikTok/Reels) or `16:9` (YouTube)
4. **Add slides**:
   - Enter narration text
   - Upload image (JPG/PNG, up to 10 MB)
   - Click "➕ Add Slide"
5. **Generate video**:
   - Click "🎬 Generate Video"
   - Monitor progress in real-time
6. **Download**: Video appears for playback and download

---

## 🔌 API Reference

### Base URL
```
http://localhost:8000/api/v1
```

### Endpoints

#### 1. Get Available Languages
```http
GET /languages
```

**Response:**
```json
[
  "ar-SA",
  "de-DE",
  "en-US",
  "es-ES",
  "fr-FR",
  "ru-RU",
  "zh-CN"
]
```

---

#### 2. Get Voices for Language
```http
GET /voices?language=en-US
```

**Query Parameters:**
- `language` (optional): Language code (e.g., `en-US`)

**Response:**
```json
[
  {
    "short_name": "en-US-AriaNeural",
    "gender": "Female",
    "locale": "en-US"
  },
  {
    "short_name": "en-US-GuyNeural",
    "gender": "Male",
    "locale": "en-US"
  }
]
```

---

#### 3. Generate Video (Manual Mode)
```http
POST /manual/generate
```

**Request Body:**
```json
{
  "slides": [
    {
      "text": "Welcome to our video",
      "image_path": "cache/abc123/images/slide1.jpg"
    },
    {
      "text": "This is the second slide",
      "image_path": "cache/abc123/images/slide2.jpg"
    }
  ],
  "voice": "en-US-AriaNeural",
  "resolution": "9:16"
}
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "video_path": null,
  "video_url": null,
  "file_size_mb": null,
  "duration_seconds": null,
  "error": null
}
```

---

#### 4. Generate Video (External Mode)
```http
POST /external/generate
```

**Request Body:**
```json
{
  "slides": [
    {
      "text": "AI-generated content",
      "image_url": "https://example.com/image1.jpg"
    }
  ],
  "voice": "en-US-AriaNeural",
  "resolution": "16:9"
}
```

**Response:** Same as manual mode

---

#### 5. Check Job Status
```http
GET /status/{job_id}
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress": 0.65,
  "current_step": "Assembling video...",
  "video_path": null,
  "error": null,
  "created_at": null,
  "completed_at": null
}
```

**Status Values:**
- `queued`: Job waiting to start
- `processing`: Video generation in progress
- `completed`: Video ready for download
- `failed`: Error occurred (check `error` field)

---

#### 6. Download Video
```http
GET /download/{job_id}
```

**Response:** MP4 file (video/mp4)

---

## 📋 API Usage Examples

### Python (requests)

```python
import requests
import time

API_BASE = "http://localhost:8000/api/v1"

# 1. Get available voices
languages = requests.get(f"{API_BASE}/languages").json()
print(f"Languages: {languages}")

voices = requests.get(f"{API_BASE}/voices", params={"language": "en-US"}).json()
print(f"Voices: {[v['short_name'] for v in voices]}")

# 2. Submit generation job
payload = {
    "slides": [
        {
            "text": "Hello from API",
            "image_path": "cache/test/image1.jpg"
        }
    ],
    "voice": "en-US-AriaNeural",
    "resolution": "9:16"
}

response = requests.post(f"{API_BASE}/manual/generate", json=payload)
job_id = response.json()["job_id"]
print(f"Job ID: {job_id}")

# 3. Poll for completion
while True:
    status = requests.get(f"{API_BASE}/status/{job_id}").json()
    print(f"Progress: {status['progress']:.1%} - {status['current_step']}")
    
    if status["status"] == "completed":
        print("✅ Video ready!")
        break
    elif status["status"] == "failed":
        print(f"❌ Failed: {status['error']}")
        break
    
    time.sleep(2)

# 4. Download video
video = requests.get(f"{API_BASE}/download/{job_id}")
with open("output.mp4", "wb") as f:
    f.write(video.content)
print("Downloaded!")
```

### cURL

```bash
# Get languages
curl http://localhost:8000/api/v1/languages

# Get voices
curl "http://localhost:8000/api/v1/voices?language=en-US"

# Submit job
curl -X POST http://localhost:8000/api/v1/manual/generate \
  -H "Content-Type: application/json" \
  -d '{
    "slides": [{"text": "Test", "image_path": "cache/test/img.jpg"}],
    "voice": "en-US-AriaNeural",
    "resolution": "9:16"
  }'

# Check status
curl http://localhost:8000/api/v1/status/550e8400-e29b-41d4-a716-446655440000

# Download
curl -O http://localhost:8000/api/v1/download/550e8400-e29b-41d4-a716-446655440000
```
