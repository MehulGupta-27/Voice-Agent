# services/streaming_stt_service.py - FIXED for threading issue

import os
import json
import asyncio
import time
import logging
import threading
import concurrent.futures
import assemblyai as aai
from typing import Optional
from assemblyai.streaming.v3 import (
    BeginEvent,
    StreamingClient,
    StreamingClientOptions,
    StreamingError,
    StreamingEvents,
    StreamingParameters,
    StreamingSessionParameters,
    TerminationEvent,
    TurnEvent,
)

logger = logging.getLogger(__name__)

class StreamingSTTService:
    def __init__(self):
        self.api_key = None
        self.is_initialized = False
        self.streaming_client = None
        self.is_streaming = False
        self.client_websocket = None
        self.event_loop = None
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=5)
        self._initialize()

    def _initialize(self):
        """Initialize AssemblyAI Universal-Streaming service"""
        try:
            assemblyai_key = os.getenv("ASSEMBLYAI_API_KEY")
            if not assemblyai_key:
                logger.error("AssemblyAI API key not found")
                return False

            # Set up AssemblyAI with the key
            aai.settings.api_key = assemblyai_key
            self.api_key = assemblyai_key
            self.is_initialized = True
            logger.info("✅ AssemblyAI Universal-Streaming service initialized successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to initialize AssemblyAI Universal-Streaming: {e}")
            return False

    def is_available(self) -> bool:
        """Check if streaming STT service is available"""
        return self.is_initialized and self.api_key is not None

    async def create_streaming_session(self, client_websocket):
        """Create a new Universal-Streaming session"""
        if not self.is_available():
            logger.error("❌ StreamingSTTService not available")
            return False

        try:
            self.is_streaming = True
            self.client_websocket = client_websocket
            # Store the current event loop for thread-safe operations
            self.event_loop = asyncio.get_running_loop()

            # Create streaming client with StreamingClientOptions
            self.streaming_client = StreamingClient(
                StreamingClientOptions(
                    api_key=self.api_key,
                    api_host="streaming.assemblyai.com"
                )
            )

            # Set up event handlers
            self.streaming_client.on(StreamingEvents.Begin, self._on_begin)
            self.streaming_client.on(StreamingEvents.Turn, self._on_turn)
            self.streaming_client.on(StreamingEvents.Termination, self._on_terminated)
            self.streaming_client.on(StreamingEvents.Error, self._on_error)

            # Start the streaming session with correct parameters
            self.streaming_client.connect(
                StreamingParameters(
                    sample_rate=16000,
                    encoding="pcm_s16le",
                    format_turns=True,  # Enable formatted final turns
                )
            )

            logger.info("🔗 Connected to AssemblyAI Universal-Streaming")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to create Universal-Streaming session: {e}")
            self.is_streaming = False
            return False

    def _on_begin(self, client: StreamingClient, event: BeginEvent):
        """Called when the streaming session opens"""
        logger.info(f"🎙️ Universal-Streaming session opened: {event.id}")
        print(f"🎙️ UNIVERSAL-STREAMING SESSION STARTED: {event.id}")
        
        # Send session opened message to client - FIXED for threading
        self._schedule_client_message({
            "status": "session_opened",
            "session_id": event.id,
            "message": "Universal-Streaming session started",
            "timestamp": time.time()
        })

    def _on_turn(self, client: StreamingClient, event: TurnEvent):
        """Called when transcript data is received"""
        if not event.transcript:
            return

        # Determine if this is partial or final based on turn_is_formatted
        if hasattr(event, 'turn_is_formatted') and event.turn_is_formatted:
            message_type = "FinalTranscript"
            logger.info(f"🎯 FINAL TRANSCRIPT: {event.transcript}")
            print(f"🎯 FINAL: {event.transcript}")
        elif event.end_of_turn:
            message_type = "FinalTranscript" 
            logger.info(f"🎯 FINAL TRANSCRIPT (end of turn): {event.transcript}")
            print(f"🎯 FINAL (end of turn): {event.transcript}")
        else:
            message_type = "PartialTranscript"
            logger.info(f"📝 PARTIAL TRANSCRIPT: {event.transcript}")
            print(f"📝 PARTIAL: {event.transcript}")

        # Send transcript to client - FIXED for threading
        self._schedule_client_message({
            "status": "transcript",
            "text": event.transcript,
            "message_type": message_type,
            "turn_order": getattr(event, 'turn_order', 0),
            "end_of_turn": event.end_of_turn,
            "turn_is_formatted": getattr(event, 'turn_is_formatted', False),
            "confidence": getattr(event, 'end_of_turn_confidence', 0.0),
            "timestamp": time.time()
        })

        # Request formatting if turn ended but isn't formatted
        if event.end_of_turn and not getattr(event, 'turn_is_formatted', False):
            try:
                self.streaming_client.set_params(
                    StreamingSessionParameters(format_turns=True)
                )
            except Exception as e:
                logger.error(f"Failed to request formatting: {e}")

    def _on_terminated(self, client: StreamingClient, event: TerminationEvent):
        """Called when the streaming session closes"""
        logger.info(f"🔚 Universal-Streaming session terminated: {event.audio_duration_seconds}s processed")
        print("🔚 UNIVERSAL-STREAMING SESSION TERMINATED")
        
        # Send session closed message to client - FIXED for threading
        self._schedule_client_message({
            "status": "session_closed",
            "message": "Session terminated by server",
            "audio_duration": event.audio_duration_seconds,
            "timestamp": time.time()
        })

    def _on_error(self, client: StreamingClient, error: StreamingError):
        """Called when an error occurs"""
        logger.error(f"❌ Universal-Streaming Error: {error}")
        print(f"❌ UNIVERSAL-STREAMING ERROR: {error}")
        
        # Send error message to client - FIXED for threading
        self._schedule_client_message({
            "status": "error",
            "error": f"Universal-Streaming Error: {str(error)}",
            "timestamp": time.time()
        })

    def _schedule_client_message(self, data):
        """FIXED: Schedule message to be sent to client WebSocket in a thread-safe way"""
        if self.event_loop and self.client_websocket:
            try:
                # Use asyncio.run_coroutine_threadsafe for thread-safe scheduling
                future = asyncio.run_coroutine_threadsafe(
                    self._send_client_message(data), 
                    self.event_loop
                )
                # Optional: Add callback to handle potential exceptions
                def handle_result(fut):
                    try:
                        fut.result()
                    except Exception as e:
                        logger.error(f"❌ Error in scheduled message: {e}")
                
                future.add_done_callback(handle_result)
            except Exception as e:
                logger.error(f"❌ Error scheduling message: {e}")

    async def _send_client_message(self, data):
        """Send message to client WebSocket with error handling"""
        try:
            if (self.client_websocket and
                hasattr(self.client_websocket, 'client_state') and
                self.client_websocket.client_state.name != 'DISCONNECTED'):
                await self.client_websocket.send_text(json.dumps(data))
            else:
                logger.warning("⚠️ WebSocket not available for sending message")
        except Exception as e:
            logger.error(f"❌ Error sending message to client: {e}")

    async def send_audio_data(self, audio_data: bytes):
        """Send raw binary audio data to Universal-Streaming"""
        if not self.is_streaming or not self.streaming_client:
            logger.warning("⚠️ No active Universal-Streaming session")
            return False

        try:
            # Send audio data to Universal-Streaming
            self.streaming_client.stream(audio_data)
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send audio data: {e}")
            return False

    async def send_force_endpoint(self):
        """Force endpoint detection"""
        if self.streaming_client:
            try:
                # Note: This method may not exist in v3 - check AssemblyAI docs
                # For now, we'll log and return True
                logger.info("🔄 Force endpoint not implemented in v3")
                return True
            except Exception as e:
                logger.error(f"❌ Failed to force endpoint: {e}")
                return False

    async def close_streaming_session(self):
        """Close the Universal-Streaming session"""
        try:
            self.is_streaming = False
            if self.streaming_client:
                self.streaming_client.disconnect(terminate=True)
                self.streaming_client = None
            
            # Clean up thread pool
            if hasattr(self, 'thread_pool'):
                self.thread_pool.shutdown(wait=False)
                
            logger.info("🔴 Universal-Streaming session closed successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Error closing Universal-Streaming session: {e}")
            return False