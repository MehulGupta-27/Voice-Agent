import os
import logging
import asyncio
import json
import websockets
import assemblyai as aai
from typing import Callable, Optional

logger = logging.getLogger(__name__)

class StreamingTranscriptionService:
    def __init__(self):
        self.transcriber = None
        self.is_initialized = False
        self.websocket_connection = None
        self.transcription_callback = None
        self._initialize()
    
    def _initialize(self):
        """Initialize AssemblyAI streaming service"""
        try:
            assemblyai_key = os.getenv("ASSEMBLYAI_API_KEY")
            if not assemblyai_key:
                logger.error("AssemblyAI API key not found")
                return False
            
            aai.settings.api_key = assemblyai_key
            self.is_initialized = True
            logger.info("✅ AssemblyAI Streaming service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize AssemblyAI Streaming: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if streaming service is available"""
        return self.is_initialized
    
    async def start_streaming_transcription(self, on_transcript: Callable[[str], None]):
        """Start streaming transcription session"""
        if not self.is_available():
            logger.error("Streaming service not available")
            return False
        
        try:
            self.transcription_callback = on_transcript
            
            # Create transcriber with streaming configuration
            config = aai.TranscriptionConfig(
                sample_rate=16000,
                language_code="en",
                word_boost=["AI", "assistant", "voice", "transcription"],
                boost_param="high"
            )
            
            self.transcriber = aai.RealtimeTranscriber(
                sample_rate=16000,
                on_data=self._on_data,
                on_error=self._on_error,
                on_open=self._on_open,
                on_close=self._on_close,
            )
            
            # Connect to AssemblyAI streaming service
            await self.transcriber.connect()
            logger.info("✅ Connected to AssemblyAI streaming service")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start streaming transcription: {e}")
            return False
    
    def _on_open(self, session_opened: aai.RealtimeSessionOpened):
        """Called when streaming session opens"""
        logger.info(f"✅ Streaming session opened: {session_opened.session_id}")
        print(f"🎤 STREAMING TRANSCRIPTION STARTED - Session ID: {session_opened.session_id}")
    
    def _on_data(self, transcript: aai.RealtimeTranscript):
        """Called when transcript data is received"""
        if not transcript.text:
            return
        
        if isinstance(transcript, aai.RealtimeFinalTranscript):
            # Final transcript - this is the completed transcription
            logger.info(f"📝 FINAL TRANSCRIPT: {transcript.text}")
            print(f"🔵 FINAL TRANSCRIPT: '{transcript.text}'")
            print(f"📊 Confidence: {getattr(transcript, 'confidence', 'N/A')}")
            print("-" * 50)
            
            if self.transcription_callback:
                asyncio.create_task(self.transcription_callback({
                    "type": "final",
                    "text": transcript.text,
                    "confidence": getattr(transcript, 'confidence', None)
                }))
        else:
            # Partial transcript - real-time streaming results
            logger.info(f"📝 PARTIAL TRANSCRIPT: {transcript.text}")
            print(f"⚪ PARTIAL: '{transcript.text}'")
            
            if self.transcription_callback:
                asyncio.create_task(self.transcription_callback({
                    "type": "partial", 
                    "text": transcript.text
                }))
    
    def _on_error(self, error: aai.RealtimeError):
        """Called when an error occurs"""
        logger.error(f"❌ Streaming transcription error: {error}")
        print(f"❌ TRANSCRIPTION ERROR: {error}")
    
    def _on_close(self):
        """Called when streaming session closes"""
        logger.info("🔴 Streaming session closed")
        print("🔴 STREAMING TRANSCRIPTION ENDED")
    
    async def send_audio_data(self, audio_data: bytes):
        """Send audio data to AssemblyAI for transcription"""
        if self.transcriber:
            try:
                self.transcriber.stream(audio_data)
            except Exception as e:
                logger.error(f"Error sending audio data: {e}")
    
    async def stop_streaming(self):
        """Stop streaming transcription"""
        if self.transcriber:
            try:
                await self.transcriber.close()
                logger.info("✅ Streaming transcription stopped")
                print("🛑 STREAMING TRANSCRIPTION STOPPED")
            except Exception as e:
                logger.error(f"Error stopping streaming: {e}")
        
        self.transcriber = None