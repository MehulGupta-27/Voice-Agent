import os
import time
import logging
import assemblyai as aai
from schemas import TranscriptionResult
import asyncio
import threading

logger = logging.getLogger(__name__)

class STTService:
    def __init__(self):
        self.transcriber = None
        self.streaming_transcriber = None
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

    def start_streaming(self):
        """Start streaming transcription session"""
        if not self.is_available():
            logger.error("STT service not available for streaming")
            return False
            
        try:
            # Configure for real-time streaming
            config = aai.TranscriptionConfig(
                sample_rate=16000,
                auto_highlights=False,
                speaker_labels=False
            )
            
            # Create streaming transcriber
            self.streaming_transcriber = aai.RealtimeTranscriber(
                sample_rate=16000,
                on_data=self._on_data,
                on_error=self._on_error,
                on_open=self._on_open,
                on_close=self._on_close,
            )
            
            # Connect to streaming service
            self.streaming_transcriber.connect()
            logger.info("🔗 Connected to AssemblyAI streaming")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start streaming: {e}")
            return False
    
    def _on_open(self, session_opened: aai.RealtimeSessionOpened):
        """Called when streaming session opens"""
        logger.info(f"🎙️ Streaming session opened: {session_opened.session_id}")
        print(f"🎙️ STREAMING SESSION OPENED: {session_opened.session_id}")

    def _on_data(self, transcript: aai.RealtimeTranscript):
        """Called when transcription data is received"""
        if not transcript.text:
            return
            
        if isinstance(transcript, aai.RealtimeFinalTranscript):
            logger.info(f"📝 FINAL TRANSCRIPTION: {transcript.text}")
            print(f"📝 FINAL TRANSCRIPTION: {transcript.text}")
        else:
            logger.info(f"⏳ PARTIAL: {transcript.text}")
            print(f"⏳ PARTIAL: {transcript.text}")

    def _on_error(self, error: aai.RealtimeError):
        """Called when streaming error occurs"""
        logger.error(f"❌ Streaming error: {error}")
        print(f"❌ STREAMING ERROR: {error}")

    def _on_close(self):
        """Called when streaming session closes"""
        logger.info("🛑 Streaming session closed")
        print("🛑 STREAMING SESSION CLOSED")
    
    def stream_audio_chunk(self, audio_data: bytes):
        """Stream audio chunk to AssemblyAI"""
        try:
            if self.streaming_transcriber:
                self.streaming_transcriber.stream(audio_data)
                logger.debug(f"📤 Streamed {len(audio_data)} bytes to AssemblyAI")
        except Exception as e:
            logger.error(f"❌ Error streaming audio: {e}")
    
    def stop_streaming(self):
        """Stop streaming transcription session"""
        try:
            if self.streaming_transcriber:
                self.streaming_transcriber.close()
                self.streaming_transcriber = None
                logger.info("🔌 Disconnected from AssemblyAI streaming")
        except Exception as e:
            logger.error(f"❌ Error stopping streaming: {e}")

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
