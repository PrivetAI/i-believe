"""
FastAPI Application for Video Generator
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.routes import router
from core.utils.logger import setup_logger, get_logger

# Setup logging
log_file = Path("logs/api.log")
log_file.parent.mkdir(parents=True, exist_ok=True)
setup_logger("root", str(log_file))
logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="AI Video Generator API",
    description="Generate videos with TTS narration, subtitles, and effects",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router, prefix="/api/v1", tags=["video"])


@app.on_event("startup")
async def startup_event():
    """Startup tasks"""
    logger.info("="*50)
    logger.info("AI Video Generator API Starting")
    logger.info("="*50)
    
    # Create necessary directories
    Path("cache").mkdir(exist_ok=True)
    Path("output").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)
    
    logger.info("✓ Directories initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown tasks"""
    logger.info("AI Video Generator API Shutting Down")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "AI Video Generator API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )