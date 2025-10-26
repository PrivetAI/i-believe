"""
Edge TTS service for text-to-speech generation
"""
import asyncio
import edge_tts
from pathlib import Path
from typing import List, Dict
from pydub import AudioSegment
from core.utils.logger import get_logger

logger = get_logger(__name__)


class TTSService:
    """Service for generating text-to-speech audio using Edge TTS"""
    
    @staticmethod
    async def _get_voices_async() -> List[Dict]:
        """Get available voices from Edge TTS"""
        voices = await edge_tts.list_voices()
        return voices
    
    @staticmethod
    def get_voices(language: str = None) -> List[Dict]:
        """
        Get available voices, optionally filtered by language
        
        Args:
            language: Optional language code (e.g., 'en-US', 'es-ES')
            
        Returns:
            List of voice dictionaries with 'Name' and 'ShortName' keys
        """
        try:
            logger.info("Fetching available voices from Edge TTS")
            voices = asyncio.run(TTSService._get_voices_async())
            
            if language:
                voices = [v for v in voices if v.get('Locale', '').startswith(language)]
                logger.info(f"Filtered {len(voices)} voices for language: {language}")
            else:
                logger.info(f"Retrieved {len(voices)} total voices")
            
            return voices
        except Exception as e:
            logger.error(f"Failed to fetch voices: {e}")
            raise
    
    @staticmethod
    async def _generate_audio_async(text: str, voice: str, output_path: str) -> None:
        """Generate audio file asynchronously"""
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
    
    @staticmethod
    def generate_audio(text: str, voice: str, output_path: str) -> float:
        """
        Generate audio from text using specified voice
        
        Args:
            text: Text to convert to speech
            voice: Voice identifier (e.g., 'en-US-AriaNeural')
            output_path: Path where audio file will be saved
            
        Returns:
            Duration of generated audio in seconds
        """
        try:
            logger.info(f"Generating TTS audio with voice: {voice}")
            logger.debug(f"Text length: {len(text)} characters")
            
            # Create output directory if needed
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Generate audio
            asyncio.run(TTSService._generate_audio_async(text, voice, output_path))
            
            # Get duration using pydub
            audio = AudioSegment.from_file(output_path)
            duration = len(audio) / 1000.0  # Convert ms to seconds
            
            logger.info(f"Audio generated successfully: {duration:.2f}s")
            return duration
            
        except Exception as e:
            logger.error(f"Failed to generate audio: {e}")
            raise
    
    @staticmethod
    def get_languages() -> List[str]:
        """
        Get list of available languages
        
        Returns:
            List of language codes
        """
        try:
            voices = TTSService.get_voices()
            languages = sorted(list(set(v.get('Locale', '')[:5] for v in voices if v.get('Locale'))))
            return languages
        except Exception as e:
            logger.error(f"Failed to get languages: {e}")
            return []