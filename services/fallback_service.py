import os
import logging
import hashlib
import base64
from pathlib import Path
from services.tts_service import TTSService

logger = logging.getLogger(__name__)

FALLBACK_RESPONSES = {
    "stt_error": "I'm having trouble understanding your audio right now. Please try speaking more clearly or check your microphone.",
    "llm_error": "I'm having trouble connecting right now. My AI brain needs a moment to reboot. Please try again in a few seconds.",
    "tts_error": "I'm having trouble connecting right now. I can understand you, but I'm having trouble speaking right now.",
    "network_error": "I'm having trouble connecting right now. Please check your internet connection and try again.",
    "general_error": "I'm having trouble connecting right now. Something unexpected happened. Please try again in a moment."
}

class FallbackAudioService:
    def __init__(self, fallback_audio_dir: Path):
        self.fallback_audio_dir = fallback_audio_dir
        self.tts_service = TTSService()
        
    async def generate_fallback_audio_url(self, text: str) -> str:
        """Generate fallback audio using same voice as main TTS (Murf), with gTTS backup"""
        try:
            text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
            murf_filename = f"murf_fallback_{text_hash}.mp3"
            murf_file_path = self.fallback_audio_dir / murf_filename
            
            if murf_file_path.exists():
                logger.info(f"Using existing Murf fallback audio: {murf_filename}")
                return f"http://localhost:8000/fallback-audio/{murf_filename}"
            
            logger.info(f"Generating fallback audio using Murf API for: '{text[:50]}...'")
            
            murf_result = await self.tts_service.generate_fallback_audio(text, murf_file_path)
            if murf_result:
                logger.info(f"✅ Murf fallback audio saved: {murf_file_path}")
                return f"http://localhost:8000/fallback-audio/{murf_filename}"
            
            logger.warning("Murf API failed for fallback, using gTTS with faster speed")
            return await self._generate_gtts_fallback_audio(text)
            
        except Exception as e:
            logger.error(f"Failed to generate fallback audio: {e}")
            return self._create_web_speech_fallback(text)

    async def _generate_gtts_fallback_audio(self, text: str) -> str:
        """Generate fallback audio using gTTS with faster speed and better settings"""
        try:
            from gtts import gTTS
            
            text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
            filename = f"gtts_fallback_{text_hash}.mp3"
            file_path = self.fallback_audio_dir / filename
            
            if file_path.exists():
                logger.info(f"Using existing gTTS fallback audio: {filename}")
                return f"http://localhost:8000/fallback-audio/{filename}"
            
            logger.info("Generating gTTS fallback with optimized settings...")
            
            tts = gTTS(
                text=text, 
                lang='en', 
                slow=False,
                tld='com'
            )
            tts.save(str(file_path))
            
            logger.info(f"✅ gTTS fallback audio saved: {file_path}")
            return f"http://localhost:8000/fallback-audio/{filename}"
            
        except ImportError:
            logger.warning("gTTS not available, using Web Speech API fallback")
            return self._create_web_speech_fallback(text)
        except Exception as e:
            logger.error(f"gTTS fallback generation failed: {e}")
            return self._create_web_speech_fallback(text)

    def _create_web_speech_fallback(self, text: str) -> str:
        """Create a fallback that uses browser's Web Speech API"""
        logger.info("Using Web Speech API fallback")
        
        text_base64 = base64.b64encode(text.encode('utf-8')).decode('utf-8')
        return f"web-speech:{text_base64}"
    
    def get_fallback_message(self, error_type: str) -> str:
        """Get appropriate fallback message for error type"""
        return FALLBACK_RESPONSES.get(error_type, FALLBACK_RESPONSES["general_error"])