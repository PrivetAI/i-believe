"""
Whisper service for speech-to-text with word-level timestamps
"""
from faster_whisper import WhisperModel
from typing import List, Dict
from utils.logger import get_logger
import config

logger = get_logger(__name__)


class WhisperService:
    """Service for transcribing audio with word-level timestamps"""
    
    def __init__(self, model_size: str = config.WHISPER_MODEL):
        """
        Initialize Whisper service
        
        Args:
            model_size: Whisper model size (tiny, base, small, medium, large)
        """
        self.model_size = model_size
        self.model = None
        logger.info(f"WhisperService initialized with model size: {model_size}")
    
    def _load_model(self):
        """Lazy load the Whisper model"""
        if self.model is None:
            logger.info(f"Loading Whisper model: {self.model_size}")
            self.model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
            logger.info("Whisper model loaded successfully")
    
    def transcribe_with_timestamps(self, audio_path: str) -> List[Dict]:
        """
        Transcribe audio and extract word-level timestamps
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            List of dictionaries with 'word', 'start', 'end' keys
        """
        try:
            self._load_model()
            logger.info(f"Transcribing audio: {audio_path}")
            
            # Transcribe with word timestamps
            segments, info = self.model.transcribe(
                audio_path,
                word_timestamps=True,
                language=None  # Auto-detect
            )
            
            logger.info(f"Detected language: {info.language} (probability: {info.language_probability:.2f})")
            
            # Extract words with timestamps
            words = []
            for segment in segments:
                if hasattr(segment, 'words') and segment.words:
                    for word in segment.words:
                        words.append({
                            'word': word.word.strip(),
                            'start': word.start,
                            'end': word.end
                        })
            
            logger.info(f"Extracted {len(words)} words with timestamps")
            logger.debug(f"First few words: {words[:5]}")
            
            return words
            
        except Exception as e:
            logger.error(f"Failed to transcribe audio: {e}")
            raise