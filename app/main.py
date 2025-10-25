"""
AI Video Generator - Streamlit Main Application with Timer
"""
import streamlit as st
import uuid
import shutil
import sys
import time
from pathlib import Path
from PIL import Image
import io

# Add app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

import config
from models.slide import Slide
from services.tts_service import TTSService
from services.whisper_service import WhisperService
from services.video_service import VideoService
from utils.logger import setup_logger, get_logger

# Setup logging
log_file = Path("logs/app.log")
log_file.parent.mkdir(parents=True, exist_ok=True)
setup_logger("root", str(log_file))
logger = get_logger(__name__)

# Page config
st.set_page_config(
    page_title="AI Video Generator",
    page_icon="🎬",
    layout="wide"
)

# Initialize session state
if 'slides' not in st.session_state:
    st.session_state.slides = []
if 'generation_id' not in st.session_state:
    st.session_state.generation_id = None
if 'generated_video_path' not in st.session_state:
    st.session_state.generated_video_path = None
if 'voices_cache' not in st.session_state:
    st.session_state.voices_cache = None
if 'languages_cache' not in st.session_state:
    st.session_state.languages_cache = None
if 'last_generation_time' not in st.session_state:
    st.session_state.last_generation_time = None


def get_cache_dir(generation_id: str) -> Path:
    """Get cache directory for current generation"""
    cache_dir = Path("cache") / generation_id
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def cleanup_cache(generation_id: str):
    """Clean up cache directory after successful generation"""
    if config.CACHE_AUTO_CLEANUP:
        cache_dir = Path("cache") / generation_id
        if cache_dir.exists():
            try:
                shutil.rmtree(cache_dir)
                logger.info(f"Cache cleaned up: {generation_id}")
            except Exception as e:
                logger.warning(f"Failed to cleanup cache: {e}")


def save_uploaded_image(uploaded_file, generation_id: str) -> str:
    """Save uploaded image to cache directory"""
    cache_dir = get_cache_dir(generation_id)
    images_dir = cache_dir / "images"
    images_dir.mkdir(exist_ok=True)
    
    # Generate unique filename
    file_ext = Path(uploaded_file.name).suffix
    filename = f"{uuid.uuid4()}{file_ext}"
    file_path = images_dir / filename
    
    # Save file
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    logger.info(f"Image saved: {filename}")
    return str(file_path)


def format_time(seconds: float) -> str:
    """Format seconds to human readable time"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.1f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def generate_video(slides: list, voice: str, resolution: tuple, generation_id: str):
    """Generate video from slides with timer"""
    logger.info("=" * 50)
    logger.info("Starting video generation")
    logger.info(f"Generation ID: {generation_id}")
    logger.info(f"Slides: {len(slides)}")
    logger.info(f"Voice: {voice}")
    logger.info(f"Resolution: {resolution[0]}x{resolution[1]}")
    logger.info("=" * 50)
    
    # Start timer
    start_time = time.time()
    
    cache_dir = get_cache_dir(generation_id)
    audio_dir = cache_dir / "audio"
    audio_dir.mkdir(exist_ok=True)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    timer_text = st.empty()
    
    def update_timer():
        """Update elapsed time display"""
        elapsed = time.time() - start_time
        timer_text.info(f"⏱️ Elapsed time: {format_time(elapsed)}")
    
    try:
        # Step 1: Generate TTS for each slide
        status_text.text("Step 1/4: Generating text-to-speech audio...")
        update_timer()
        logger.info("Step 1: Generating TTS audio")
        
        step1_start = time.time()
        tts_service = TTSService()
        slide_objects = []
        
        for i, slide_data in enumerate(slides):
            logger.info(f"Generating TTS for slide {i+1}/{len(slides)}")
            
            audio_path = audio_dir / f"slide_{i}.mp3"
            duration = tts_service.generate_audio(
                slide_data['text'],
                voice,
                str(audio_path)
            )
            
            slide_obj = Slide(
                text=slide_data['text'],
                image_path=slide_data['image_path'],
                audio_path=str(audio_path),
                duration=duration
            )
            slide_objects.append(slide_obj)
            
            progress = (i + 1) / len(slides) * 0.25
            progress_bar.progress(progress)
            update_timer()
        
        step1_time = time.time() - step1_start
        logger.info(f"TTS generation completed in {step1_time:.2f}s")
        
        # Step 2: Generate word-level timestamps with Whisper
        status_text.text("Step 2/4: Generating word-level timestamps...")
        update_timer()
        logger.info("Step 2: Generating word timestamps")
        
        step2_start = time.time()
        whisper_service = WhisperService()
        words_per_slide = []
        
        for i, slide in enumerate(slide_objects):
            logger.info(f"Transcribing slide {i+1}/{len(slides)}")
            
            words = whisper_service.transcribe_with_timestamps(slide.audio_path)
            words_per_slide.append(words)
            
            progress = 0.25 + (i + 1) / len(slides) * 0.25
            progress_bar.progress(progress)
            update_timer()
        
        step2_time = time.time() - step2_start
        logger.info(f"Whisper transcription completed in {step2_time:.2f}s")
        
        # Step 3: Assemble video
        status_text.text("Step 3/4: Assembling video with effects...")
        update_timer()
        logger.info("Step 3: Assembling video")
        
        step3_start = time.time()
        progress_bar.progress(0.5)
        
        video_service = VideoService(resolution)
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"video_{generation_id}.mp4"
        
        video_path = video_service.assemble_video(
            slide_objects,
            str(output_path),
            words_per_slide
        )
        
        step3_time = time.time() - step3_start
        logger.info(f"Video assembly completed in {step3_time:.2f}s")
        
        progress_bar.progress(0.75)
        update_timer()
        
        # Step 4: Finalize
        status_text.text("Step 4/4: Finalizing video...")
        update_timer()
        logger.info("Step 4: Finalizing")
        
        progress_bar.progress(1.0)
        
        # Calculate total time
        total_time = time.time() - start_time
        
        # Show breakdown
        status_text.success(f"✅ Video generation completed!")
        timer_text.success(f"""
        ⏱️ **Generation Time Breakdown:**
        - TTS Audio: {format_time(step1_time)}
        - Whisper Timestamps: {format_time(step2_time)}
        - Video Assembly: {format_time(step3_time)}
        - **Total: {format_time(total_time)}**
        """)
        
        logger.info("Video generation successful")
        logger.info(f"Output: {video_path}")
        logger.info(f"Total time: {total_time:.2f}s")
        logger.info(f"  - TTS: {step1_time:.2f}s")
        logger.info(f"  - Whisper: {step2_time:.2f}s")
        logger.info(f"  - Assembly: {step3_time:.2f}s")
        
        # Store generation time
        st.session_state.last_generation_time = total_time
        
        # Cleanup cache
        cleanup_cache(generation_id)
        
        return video_path
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Video generation failed after {elapsed:.2f}s: {e}", exc_info=True)
        status_text.error(f"❌ Error: {str(e)}")
        timer_text.warning(f"⏱️ Failed after {format_time(elapsed)}")
        progress_bar.empty()
        raise


# Main UI
st.title("🎬 AI Video Generator")
st.markdown("Generate short-form videos with AI-powered voiceover and subtitles")
st.markdown("Текст для быстрой вставки и теста")

# Show last generation time if available
if st.session_state.last_generation_time:
    st.info(f"⏱️ Last generation took: **{format_time(st.session_state.last_generation_time)}**")

# Sidebar - Configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Voice Selection
    st.subheader("Voice Settings")
    
    # Initialize selected_voice
    selected_voice = None
    
    # Load languages
    if st.session_state.languages_cache is None:
        with st.spinner("Loading languages..."):
            try:
                st.session_state.languages_cache = TTSService.get_languages()
            except Exception as e:
                st.error(f"Failed to load languages: {e}")
                st.session_state.languages_cache = []
    
    if st.session_state.languages_cache:
        selected_language = st.selectbox(
            "Language",
            st.session_state.languages_cache,
            index=0 if st.session_state.languages_cache else None
        )
        
        # Load voices for selected language
        if st.button("Load Voices") or st.session_state.voices_cache is not None:
            if st.session_state.voices_cache is None:
                with st.spinner("Loading voices..."):
                    try:
                        voices = TTSService.get_voices(selected_language)
                        st.session_state.voices_cache = voices
                    except Exception as e:
                        st.error(f"Failed to load voices: {e}")
                        st.session_state.voices_cache = []
        
        if st.session_state.voices_cache:
            voice_options = {
                f"{v['ShortName']} ({v.get('Gender', 'Unknown')})": v['ShortName']
                for v in st.session_state.voices_cache
            }
            
            if voice_options:
                selected_voice_display = st.selectbox(
                    "Voice",
                    list(voice_options.keys())
                )
                selected_voice = voice_options[selected_voice_display]
            else:
                st.warning("No voices available for this language")
        else:
            if st.session_state.voices_cache is not None:
                st.info("Click 'Load Voices' to see available voices")
    else:
        st.error("Failed to load languages")
    
    # Video Settings
    st.subheader("Video Settings")
    resolution_choice = st.radio(
        "Resolution",
        list(config.VIDEO_RESOLUTIONS.keys()),
        index=0
    )
    resolution = config.VIDEO_RESOLUTIONS[resolution_choice]

# Main Content
st.header("📝 Manual Upload Mode")

# Slide input form
with st.form("slide_form", clear_on_submit=True):
    col1, col2 = st.columns([2, 1])
    
    with col1:
        slide_text = st.text_area(
            "Slide Text",
            placeholder="Enter the text for this slide...",
            height=150
        )
    
    with col2:
        uploaded_image = st.file_uploader(
            "Upload Image",
            type=config.ALLOWED_IMAGE_EXTENSIONS,
            help=f"Supported formats: {', '.join(config.ALLOWED_IMAGE_EXTENSIONS)}"
        )
    
    submitted = st.form_submit_button("➕ Add Slide", type="primary")
    
    if submitted:
        if not slide_text or not slide_text.strip():
            st.error("Please enter text for the slide")
        elif not uploaded_image:
            st.error("Please upload an image")
        else:
            # Generate new generation ID if needed
            if st.session_state.generation_id is None:
                st.session_state.generation_id = str(uuid.uuid4())
            
            # Save image
            image_path = save_uploaded_image(
                uploaded_image,
                st.session_state.generation_id
            )
            
            # Add to slides
            st.session_state.slides.append({
                'text': slide_text.strip(),
                'image_path': image_path,
                'image_name': uploaded_image.name
            })
            
            st.success(f"✅ Slide {len(st.session_state.slides)} added!")
            st.rerun()

# Display slides list
if st.session_state.slides:
    st.header("📋 Slides List")
    
    for i, slide in enumerate(st.session_state.slides):
        with st.expander(f"Slide {i+1}: {slide['text'][:50]}..."):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.text_area(
                    "Text",
                    value=slide['text'],
                    disabled=True,
                    key=f"text_{i}",
                    height=100
                )
            
            with col2:
                try:
                    img = Image.open(slide['image_path'])
                    st.image(img, caption=slide['image_name'], use_column_width=True)
                except Exception as e:
                    st.error(f"Failed to load image: {e}")
                
                if st.button("🗑️ Delete", key=f"delete_{i}"):
                    st.session_state.slides.pop(i)
                    st.rerun()
    
    # Generation controls
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
            st.error("Please select a voice in the sidebar")
        else:
            # Generate new ID for this generation
            generation_id = str(uuid.uuid4())
            
            with st.spinner("Generating video..."):
                try:
                    video_path = generate_video(
                        st.session_state.slides,
                        selected_voice,
                        resolution,
                        generation_id
                    )
                    
                    st.session_state.generated_video_path = video_path
                    
                except Exception as e:
                    st.error(f"Failed to generate video: {str(e)}")
                    logger.error(f"Generation error: {e}", exc_info=True)

else:
    st.info("👆 Add slides above to get started")

# Display generated video
if st.session_state.generated_video_path:
    st.divider()
    st.header("🎥 Generated Video")
    
    video_path = Path(st.session_state.generated_video_path)
    
    if video_path.exists():
        # Video player
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            with open(video_path, 'rb') as video_file:
                video_bytes = video_file.read()
                st.video(video_bytes)
        
        # Download button and info
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
            st.caption(f"📊 File size: {file_size_mb:.2f} MB | Resolution: {resolution[0]}x{resolution[1]}")
    else:
        st.error("Video file not found")

# Logs section
with st.expander("📋 View Logs"):
    log_file_path = Path("logs/app.log")
    if log_file_path.exists():
        try:
            with open(log_file_path, 'r') as f:
                logs = f.readlines()
                # Show last 100 lines
                recent_logs = ''.join(logs[-100:])
                st.text_area(
                    "Recent Logs",
                    value=recent_logs,
                    height=400,
                    disabled=True
                )
        except Exception as e:
            st.error(f"Failed to load logs: {e}")
    else:
        st.info("No logs available yet")