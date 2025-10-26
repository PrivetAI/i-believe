"""
API Routes for video generation
"""
import uuid
from pathlib import Path
from typing import List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.schemas import (
    GenerateVideoRequest,
    VideoResponse,
    VoiceInfo,
    JobStatusResponse
)
from core.pipeline import VideoPipeline
from services.tts_service import TTSService
import config
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

# In-memory job storage (replace with Redis/DB in production)
jobs = {}


def background_generate_video(
    job_id: str,
    slides_data: List[dict],
    voice: str,
    resolution: tuple,
    output_path: str
):
    """Background task for video generation"""
    try:
        jobs[job_id]['status'] = 'processing'
        
        def progress_callback(progress: float, message: str):
            jobs[job_id]['progress'] = progress
            jobs[job_id]['current_step'] = message
            logger.info(f"Job {job_id}: {progress:.1%} - {message}")
        
        pipeline = VideoPipeline(generation_id=job_id)
        result = pipeline.generate(
            slides_data,
            voice,
            resolution,
            output_path,
            progress_callback
        )
        
        jobs[job_id]['status'] = 'completed'
        jobs[job_id]['video_path'] = result['video_path']
        jobs[job_id]['progress'] = 1.0
        jobs[job_id]['file_size_mb'] = result['file_size_mb']
        jobs[job_id]['duration_seconds'] = result['duration']
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        jobs[job_id]['status'] = 'failed'
        jobs[job_id]['error'] = str(e)


@router.post("/manual/generate", response_model=VideoResponse)
async def generate_video_manual(
    request: GenerateVideoRequest,
    background_tasks: BackgroundTasks
):
    """
    Generate video from manually uploaded slides (existing workflow)
    Images must already be uploaded to local cache
    """
    job_id = str(uuid.uuid4())
    
    # Validate resolution
    resolution = config.VIDEO_RESOLUTIONS.get(request.resolution.value)
    if not resolution:
        raise HTTPException(400, f"Invalid resolution: {request.resolution}")
    
    # Validate slides
    for i, slide in enumerate(request.slides):
        if not slide.image_path:
            raise HTTPException(400, f"Slide {i}: image_path is required for manual mode")
        
        if not Path(slide.image_path).exists():
            raise HTTPException(400, f"Slide {i}: image not found at {slide.image_path}")
    
    # Prepare output path
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    output_path = str(output_dir / f"video_{job_id}.mp4")
    
    # Prepare slides data
    slides_data = [
        {'text': s.text, 'image_path': s.image_path}
        for s in request.slides
    ]
    
    # Initialize job
    jobs[job_id] = {
        'status': 'queued',
        'progress': 0.0,
        'current_step': 'Queued',
        'video_path': None,
        'error': None
    }
    
    # Start background task
    background_tasks.add_task(
        background_generate_video,
        job_id,
        slides_data,
        request.voice,
        resolution,
        output_path
    )
    
    logger.info(f"Job {job_id} queued (manual mode)")
    
    return VideoResponse(
        job_id=job_id,
        status='queued'
    )


@router.post("/external/generate", response_model=VideoResponse)
async def generate_video_external(
    request: GenerateVideoRequest,
    background_tasks: BackgroundTasks
):
    """
    Generate video from external source (AI generator)
    Images will be downloaded from provided URLs
    """
    job_id = str(uuid.uuid4())
    
    # Validate resolution
    resolution = config.VIDEO_RESOLUTIONS.get(request.resolution.value)
    if not resolution:
        raise HTTPException(400, f"Invalid resolution: {request.resolution}")
    
    # Validate slides
    for i, slide in enumerate(request.slides):
        if not slide.image_url:
            raise HTTPException(400, f"Slide {i}: image_url is required for external mode")
    
    # Prepare output path
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    output_path = str(output_dir / f"video_{job_id}.mp4")
    
    # Prepare slides data
    slides_data = [
        {'text': s.text, 'image_url': str(s.image_url)}
        for s in request.slides
    ]
    
    # Initialize job
    jobs[job_id] = {
        'status': 'queued',
        'progress': 0.0,
        'current_step': 'Queued',
        'video_path': None,
        'error': None
    }
    
    # Start background task
    background_tasks.add_task(
        background_generate_video,
        job_id,
        slides_data,
        request.voice,
        resolution,
        output_path
    )
    
    logger.info(f"Job {job_id} queued (external mode)")
    
    return VideoResponse(
        job_id=job_id,
        status='queued'
    )


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get job status and progress"""
    if job_id not in jobs:
        raise HTTPException(404, f"Job {job_id} not found")
    
    job = jobs[job_id]
    
    return JobStatusResponse(
        job_id=job_id,
        status=job['status'],
        progress=job.get('progress'),
        current_step=job.get('current_step'),
        video_path=job.get('video_path'),
        error=job.get('error')
    )


@router.get("/download/{job_id}")
async def download_video(job_id: str):
    """Download generated video"""
    if job_id not in jobs:
        raise HTTPException(404, f"Job {job_id} not found")
    
    job = jobs[job_id]
    
    if job['status'] != 'completed':
        raise HTTPException(400, f"Job not completed: {job['status']}")
    
    video_path = job.get('video_path')
    if not video_path or not Path(video_path).exists():
        raise HTTPException(404, "Video file not found")
    
    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=Path(video_path).name
    )


@router.get("/languages", response_model=List[str])
async def get_languages():
    """Get available TTS languages"""
    try:
        languages = TTSService.get_languages()
        return languages
    except Exception as e:
        logger.error(f"Failed to get languages: {e}")
        raise HTTPException(500, f"Failed to get languages: {str(e)}")


@router.get("/voices", response_model=List[VoiceInfo])
async def get_voices(language: str = None):
    """Get available TTS voices, optionally filtered by language"""
    try:
        voices = TTSService.get_voices(language)
        
        return [
            VoiceInfo(
                short_name=v['ShortName'],
                gender=v.get('Gender'),
                locale=v.get('Locale', '')
            )
            for v in voices
        ]
    except Exception as e:
        logger.error(f"Failed to get voices: {e}")
        raise HTTPException(500, f"Failed to get voices: {str(e)}")