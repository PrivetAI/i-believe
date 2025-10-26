"""Streamlit UI - calls backend API"""
import streamlit as st
import requests
import uuid
import time
from pathlib import Path
from PIL import Image
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from utils.logger import setup_logger, get_logger

# Setup logging
log_file = Path("logs/ui.log")
log_file.parent.mkdir(parents=True, exist_ok=True)
setup_logger("root", str(log_file))
logger = get_logger(__name__)

# API Configuration
API_BASE_URL = "http://localhost:8000/api/v1"

# Page config
st.set_page_config(page_title="AI Video Generator", page_icon="🎬", layout="wide")

# Session state
if 'slides' not in st.session_state:
    st.session_state.slides = []
if 'generation_id' not in st.session_state:
    st.session_state.generation_id = None
if 'current_job_id' not in st.session_state:
    st.session_state.current_job_id = None
if 'generated_video_path' not in st.session_state:
    st.session_state.generated_video_path = None
if 'voices_cache' not in st.session_state:
    st.session_state.voices_cache = None
if 'languages_cache' not in st.session_state:
    st.session_state.languages_cache = None


def get_cache_dir(generation_id: str) -> Path:
    cache_dir = Path("cache") / generation_id
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def save_uploaded_image(uploaded_file, generation_id: str) -> str:
    cache_dir = get_cache_dir(generation_id)
    images_dir = cache_dir / "images"
    images_dir.mkdir(exist_ok=True)
    
    file_ext = Path(uploaded_file.name).suffix
    filename = f"{uuid.uuid4()}{file_ext}"
    file_path = images_dir / filename
    
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    logger.info(f"Image saved: {filename}")
    return str(file_path)


def api_get_languages():
    """Get languages from API"""
    try:
        response = requests.get(f"{API_BASE_URL}/languages", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to get languages: {e}")
        return []


def api_get_voices(language: str):
    """Get voices from API"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/voices",
            params={"language": language},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to get voices: {e}")
        return []


def api_generate_video(slides_data, voice, resolution):
    """Submit video generation job via API"""
    try:
        payload = {
            "slides": slides_data,
            "voice": voice,
            "resolution": resolution
        }
        
        response = requests.post(
            f"{API_BASE_URL}/manual/generate",
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to submit job: {e}")
        raise


def api_get_job_status(job_id: str):
    """Get job status from API"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/status/{job_id}",
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        return None


def poll_job_status(job_id: str):
    """Poll job status until completion"""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    while True:
        status = api_get_job_status(job_id)
        
        if not status:
            status_text.error("Failed to get job status")
            break
        
        progress = status.get('progress', 0)
        current_step = status.get('current_step', 'Processing...')
        
        progress_bar.progress(progress)
        status_text.text(f"Status: {status['status']} - {current_step}")
        
        if status['status'] == 'completed':
            status_text.success("✅ Video generation completed!")
            return status['video_path']
        
        elif status['status'] == 'failed':
            error = status.get('error', 'Unknown error')
            status_text.error(f"❌ Generation failed: {error}")
            return None
        
        time.sleep(1)


# Main UI
st.title("🎬 AI Video Generator")
st.markdown("Generate short-form videos with AI-powered voiceover and subtitles")

# Sidebar - Configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    st.subheader("Voice Settings")
    
    selected_voice = None
    
    if st.session_state.languages_cache is None:
        with st.spinner("Loading languages..."):
            st.session_state.languages_cache = api_get_languages()
    
    if st.session_state.languages_cache:
        selected_language = st.selectbox(
            "Language",
            st.session_state.languages_cache,
            index=0
        )
        
        if st.button("Load Voices") or st.session_state.voices_cache is not None:
            if st.session_state.voices_cache is None:
                with st.spinner("Loading voices..."):
                    voices = api_get_voices(selected_language)
                    st.session_state.voices_cache = voices
        
        if st.session_state.voices_cache:
            voice_options = {
                f"{v['short_name']} ({v.get('gender', 'Unknown')})": v['short_name']
                for v in st.session_state.voices_cache
            }
            
            if voice_options:
                selected_voice_display = st.selectbox("Voice", list(voice_options.keys()))
                selected_voice = voice_options[selected_voice_display]
            else:
                st.warning("No voices available")
        else:
            if st.session_state.voices_cache is not None:
                st.info("Click 'Load Voices'")
    else:
        st.error("Failed to load languages")
    
    st.subheader("Video Settings")
    resolution_choice = st.radio(
        "Resolution",
        list(config.VIDEO_RESOLUTIONS.keys()),
        index=0
    )

# Main Content
st.header("📝 Manual Upload Mode")

with st.form("slide_form", clear_on_submit=True):
    col1, col2 = st.columns([2, 1])
    
    with col1:
        slide_text = st.text_area("Slide Text", placeholder="Enter text...", height=150)
    
    with col2:
        uploaded_image = st.file_uploader(
            "Upload Image",
            type=config.ALLOWED_IMAGE_EXTENSIONS
        )
    
    submitted = st.form_submit_button("➕ Add Slide", type="primary")
    
    if submitted:
        if not slide_text or not slide_text.strip():
            st.error("Please enter text")
        elif not uploaded_image:
            st.error("Please upload an image")
        else:
            if st.session_state.generation_id is None:
                st.session_state.generation_id = str(uuid.uuid4())
            
            image_path = save_uploaded_image(uploaded_image, st.session_state.generation_id)
            
            st.session_state.slides.append({
                'text': slide_text.strip(),
                'image_path': image_path,
                'image_name': uploaded_image.name
            })
            
            st.success(f"✅ Slide {len(st.session_state.slides)} added!")
            st.rerun()

# Display slides
if st.session_state.slides:
    st.header("📋 Slides List")
    
    for i, slide in enumerate(st.session_state.slides):
        with st.expander(f"Slide {i+1}: {slide['text'][:50]}..."):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.text_area("Text", value=slide['text'], disabled=True, key=f"text_{i}", height=100)
            
            with col2:
                try:
                    img = Image.open(slide['image_path'])
                    st.image(img, caption=slide['image_name'], use_column_width=True)
                except Exception as e:
                    st.error(f"Failed to load image: {e}")
                
                if st.button("🗑️ Delete", key=f"delete_{i}"):
                    st.session_state.slides.pop(i)
                    st.rerun()
    
    st.divider()
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.info(f"Total slides: {len(st.session_state.slides)}")
    
    with col2:
        if st.button("🗑️ Clear All", use_container_width=True):
            st.session_state.slides = []
            st.session_state.generation_id = None
            st.rerun()
    
    with col3:
        generate_button = st.button(
            "🎬 Generate Video",
            type="primary",
            use_container_width=True,
            disabled=not selected_voice
        )
    
    if generate_button:
        if not selected_voice:
            st.error("Please select a voice")
        else:
            # Prepare slides data for API
            slides_data = [
                {
                    "text": slide['text'],
                    "image_path": slide['image_path']
                }
                for slide in st.session_state.slides
            ]
            
            with st.spinner("Submitting job..."):
                try:
                    # Submit job to API
                    result = api_generate_video(
                        slides_data,
                        selected_voice,
                        resolution_choice
                    )
                    
                    job_id = result['job_id']
                    st.session_state.current_job_id = job_id
                    
                    logger.info(f"Job submitted: {job_id}")
                    
                    # Poll for completion
                    video_path = poll_job_status(job_id)
                    
                    if video_path:
                        st.session_state.generated_video_path = video_path
                        st.rerun()
                    
                except Exception as e:
                    st.error(f"Failed: {str(e)}")
                    logger.error(f"Generation error: {e}", exc_info=True)
else:
    st.info("👆 Add slides above to get started")

# Display video
if st.session_state.generated_video_path:
    st.divider()
    st.header("🎥 Generated Video")
    
    video_path = Path(st.session_state.generated_video_path)
    
    if video_path.exists():
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            with open(video_path, 'rb') as video_file:
                video_bytes = video_file.read()
                st.video(video_bytes)
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.download_button(
                label="⬇️ Download Video",
                data=video_bytes,
                file_name=video_path.name,
                mime="video/mp4",
                use_container_width=True
            )
        
        with col2:
            file_size_mb = video_path.stat().st_size / (1024 * 1024)
            resolution = config.VIDEO_RESOLUTIONS[resolution_choice]
            st.caption(f"📊 File size: {file_size_mb:.2f} MB | Resolution: {resolution[0]}x{resolution[1]}")
    else:
        st.error("Video file not found")

# Logs
with st.expander("📋 View Logs"):
    log_file_path = Path("logs/ui.log")
    if log_file_path.exists():
        try:
            with open(log_file_path, 'r') as f:
                logs = f.readlines()
                recent_logs = ''.join(logs[-100:])
                st.text_area("Recent Logs", value=recent_logs, height=400, disabled=True)
        except Exception as e:
            st.error(f"Failed to load logs: {e}")
    else:
        st.info("No logs available yet")