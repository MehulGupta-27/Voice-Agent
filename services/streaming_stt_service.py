# services/streaming_stt_service.py

import os
import json
import asyncio
import time
import logging
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

    def _initialize(self) -> bool:
        """Initialize AssemblyAI Universal-Streaming service"""
        try:
            assemblyai_key = os.getenv("ASSEMBLYAI_API_KEY")
            if not assemblyai_key:
                logger.error("AssemblyAI API key not found")
                return False
            aai.settings.api_key = assemblyai_key
            self.api_key = assemblyai_key
            self.is_initialized = True
            logger.info("✅ AssemblyAI Universal-Streaming service initialized successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize AssemblyAI Universal-Streaming: {e}")
            return False

    def is_available(self) -> bool:
        return self.is_initialized and self.api_key is not None

    async def create_streaming_session(self, client_websocket) -> bool:
        if not self.is_available():
            logger.error("❌ StreamingSTTService not available")
            return False
        try:
            self.is_streaming = True
            self.client_websocket = client_websocket
            self.event_loop = asyncio.get_running_loop()
            self.streaming_client = StreamingClient(
                StreamingClientOptions(api_key=self.api_key, api_host="streaming.assemblyai.com")
            )
            # Handlers
            self.streaming_client.on(StreamingEvents.Begin, self._on_begin)
            self.streaming_client.on(StreamingEvents.Turn, self._on_turn)
            self.streaming_client.on(StreamingEvents.Termination, self._on_terminated)
            self.streaming_client.on(StreamingEvents.Error, self._on_error)

            # Start streaming
            self.streaming_client.connect(
                StreamingParameters(
                    sample_rate=16000,
                    encoding="pcm_s16le",
                    format_turns=True,  # request formatted turns up front
                )
            )
            logger.info("🔗 Connected to AssemblyAI Universal-Streaming")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to create Universal-Streaming session: {e}")
            self.is_streaming = False
            return False

    def _on_begin(self, client: StreamingClient, event: BeginEvent):
        logger.info(f"🎙️ Universal-Streaming session opened: {event.id}")
        self._schedule_client_message({
            "status": "session_opened",
            "session_id": event.id,
            "message": "Universal-Streaming session started",
            "timestamp": time.time()
        })

    def _on_turn(self, client: StreamingClient, event: TurnEvent):
        if not event.transcript:
            return

        # Only emit formatted final turns and partials; drop raw unformatted end‐of‐turn
        if getattr(event, 'turn_is_formatted', False):
            message_type = "FinalTranscript"
        elif event.end_of_turn:
            return
        else:
            message_type = "PartialTranscript"

        # Now schedule exactly one message per valid turn
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

    def _on_terminated(self, client: StreamingClient, event: TerminationEvent):
        logger.info(f"🔚 Universal-Streaming session terminated: {event.audio_duration_seconds}s processed")
        self._schedule_client_message({
            "status": "session_closed",
            "message": "Session terminated by server",
            "audio_duration": event.audio_duration_seconds,
            "timestamp": time.time()
        })

    def _on_error(self, client: StreamingClient, error: StreamingError):
        logger.error(f"❌ Universal-Streaming Error: {error}")
        self._schedule_client_message({
            "status": "error",
            "error": f"Universal-Streaming Error: {str(error)}",
            "timestamp": time.time()
        })

    def _schedule_client_message(self, data: dict):
        """Thread-safe scheduling into the asyncio loop"""
        if not self.event_loop or not self.client_websocket:
            return
        try:
            future = asyncio.run_coroutine_threadsafe(
                self._send_client_message(data), self.event_loop
            )
            def _handle(fut):
                try:
                    fut.result()
                except Exception as e:
                    logger.error(f"❌ Error sending scheduled message: {e}")
            future.add_done_callback(_handle)
        except Exception as e:
            logger.error(f"❌ Error scheduling message: {e}")

    async def _send_client_message(self, data: dict):
        try:
            if self.client_websocket and hasattr(self.client_websocket, 'client_state') and self.client_websocket.client_state.name != 'DISCONNECTED':
                await self.client_websocket.send_text(json.dumps(data))
            else:
                logger.warning("⚠️ WebSocket not available for sending message")
        except Exception as e:
            logger.error(f"❌ Error sending message to client: {e}")

    async def send_audio_data(self, audio_data: bytes) -> bool:
        if not self.is_streaming or not self.streaming_client:
            logger.warning("⚠️ No active Universal-Streaming session")
            return False
        try:
            self.streaming_client.stream(audio_data)
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send audio data: {e}")
            return False

    async def send_force_endpoint(self) -> bool:
        # No-op for v3; kept for compatibility
        logger.info("🔄 Force endpoint not implemented in v3")
        return True

    async def close_streaming_session(self) -> bool:
        try:
            self.is_streaming = False
            if self.streaming_client:
                self.streaming_client.disconnect(terminate=True)
                self.streaming_client = None
            if hasattr(self, 'thread_pool'):
                self.thread_pool.shutdown(wait=False)
            logger.info("🔴 Universal-Streaming session closed successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Error closing Universal-Streaming session: {e}")
            return False
