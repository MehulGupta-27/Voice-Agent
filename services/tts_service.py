import os
import time
import logging
import requests
from schemas import TTSResult

logger = logging.getLogger(__name__)

FALLBACK_RESPONSES = {
    "tts_error": "I'm having trouble connecting right now"
}

class TTSService:
    def __init__(self):
        self.api_key = None
        self.is_initialized = False
        self._initialize()
    
    def _initialize(self):
        """Initialize Murf TTS service"""
        try:
            murf_key = os.getenv("MURF_API_KEY")
            if not murf_key:
                logger.error("Murf API key not found")
                return False
            
            self.api_key = murf_key
            self.is_initialized = True
            logger.info("✅ Murf API key found")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to check Murf API key: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if TTS service is available"""
        return self.is_initialized and self.api_key is not None
    
    async def generate(self, text: str, voice_id: str = "en-US-marcus", max_retries: int = 3) -> TTSResult:
        """Safely generate TTS audio with retries and fallback"""
        if not self.is_available():
            return TTSResult(
                success=False,
                error="Murf TTS service not available",
                fallback_text=FALLBACK_RESPONSES["tts_error"]
            )
        
        for attempt in range(max_retries):
            try:
                logger.info(f"TTS generation attempt {attempt + 1}/{max_retries}")
                
                url = "https://api.murf.ai/v1/speech/generate-with-key"
                headers = {
                    "accept": "application/json",
                    "Content-Type": "application/json",
                    "api-key": self.api_key
                }
                payload = {
                    "text": text,
                    "voiceId": voice_id,
                    "format": "MP3"
                }
                
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                
                if response.status_code != 200:
                    logger.error(f"Murf API failed: {response.status_code} - {response.text}")
                    if attempt == max_retries - 1:
                        return TTSResult(
                            success=False,
                            error=f"TTS API failed: {response.status_code}",
                            fallback_text=FALLBACK_RESPONSES["tts_error"]
                        )
                    continue
                
                result = response.json()
                audio_url = result.get("audioFile")
                
                if not audio_url:
                    if attempt == max_retries - 1:
                        return TTSResult(
                            success=False,
                            error="No audio URL received",
                            fallback_text=FALLBACK_RESPONSES["tts_error"]
                        )
                    continue
                
                return TTSResult(
                    success=True,
                    audio_url=audio_url
                )
                
            except Exception as e:
                logger.error(f"TTS generation attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    return TTSResult(
                        success=False,
                        error=str(e),
                        fallback_text=FALLBACK_RESPONSES["tts_error"]
                    )
                time.sleep(1)
        
        return TTSResult(
            success=False,
            error="Max retries exceeded",
            fallback_text=FALLBACK_RESPONSES["tts_error"]
        )
    
    async def generate_fallback_audio(self, text: str, file_path) -> bool:
        """Generate fallback audio using Murf API (same voice as main TTS)"""
        try:
            url = "https://api.murf.ai/v1/speech/generate-with-key"
            headers = {
                "accept": "application/json",
                "Content-Type": "application/json",
                "api-key": self.api_key
            }
            
            payload = {
                "text": text,
                "voiceId": "en-US-marcus",
                "format": "MP3"
            }
            
            logger.info("Calling Murf API for fallback audio...")
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                audio_url = result.get("audioFile")
                
                if audio_url:
                    audio_response = requests.get(audio_url, timeout=30)
                    if audio_response.status_code == 200:
                        with open(file_path, 'wb') as f:
                            f.write(audio_response.content)
                        logger.info("✅ Murf fallback audio downloaded and saved")
                        return True
            
            logger.warning(f"Murf API failed for fallback: {response.status_code}")
            return False
            
        except Exception as e:
            logger.error(f"Murf fallback generation failed: {e}")
            return False