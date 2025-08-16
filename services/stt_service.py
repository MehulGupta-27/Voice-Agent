import os
import time
import logging
import assemblyai as aai
from schemas import TranscriptionResult

logger = logging.getLogger(__name__)

class STTService:
    def __init__(self):
        self.transcriber = None
        self.is_initialized = False
        self._initialize()
    
    def _initialize(self):
        """Initialize AssemblyAI service"""
        try:
            assemblyai_key = os.getenv("ASSEMBLYAI_API_KEY")
            if not assemblyai_key:
                logger.error("AssemblyAI API key not found")
                return False
            
            aai.settings.api_key = assemblyai_key
            self.transcriber = aai.Transcriber()
            self.is_initialized = True
            logger.info("✅ AssemblyAI initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize AssemblyAI: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if STT service is available"""
        return self.is_initialized and self.transcriber is not None
    
    async def transcribe(self, audio_data: bytes, max_retries: int = 3) -> TranscriptionResult:
        """Safely transcribe audio with retries and fallback"""
        if not self.is_available():
            return TranscriptionResult(
                success=False,
                error="AssemblyAI service not available",
                fallback_text="Speech transcription unavailable"
            )
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Transcription attempt {attempt + 1}/{max_retries}")
                transcript = self.transcriber.transcribe(audio_data)
                
                if transcript.status == aai.TranscriptStatus.error:
                    logger.error(f"Transcription failed: {transcript.error}")
                    if attempt == max_retries - 1:
                        return TranscriptionResult(
                            success=False,
                            error=f"Transcription failed: {transcript.error}",
                            fallback_text="Could not transcribe audio"
                        )
                    continue
                
                return TranscriptionResult(
                    success=True,
                    text=transcript.text,
                    duration=transcript.audio_duration,
                    confidence=getattr(transcript, 'confidence', None)
                )
                
            except Exception as e:
                logger.error(f"Transcription attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    return TranscriptionResult(
                        success=False,
                        error=str(e),
                        fallback_text="Transcription service error"
                    )
                time.sleep(1)
        
        return TranscriptionResult(
            success=False,
            error="Max retries exceeded",
            fallback_text="Could not process audio"
        )