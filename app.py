# Updated app.py with WebSocket Audio Streaming
# Add these imports to the existing imports in app.py
from fastapi import WebSocket, WebSocketDisconnect
from services.streaming_stt_service import StreamingSTTService
import base64
import time
import json
from fastapi import FastAPI, File, UploadFile, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import logging.config
import asyncio
import os
from pathlib import Path
import json
from typing import List, Dict
import base64
import io

# Import configurations and schemas
import config
from schemas import *

# Import services
from services.stt_service import STTService
from services.llm_service import LLMService
from services.tts_service import TTSService
from services.fallback_service import FallbackAudioService
from services.session_manager import SessionManager

import asyncio
import websockets
import json
import base64
import os
import logging
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
# Configure logging
logging.config.dictConfig(config.LOGGING_CONFIG)

# Initialize FastAPI app
# Add this after your existing services initialization
streaming_stt_service = StreamingSTTService()
app = FastAPI(title="Voice AI Assistant with Audio Streaming", version="1.0.0")


# Setup directories
def setup_directories():
    """Create necessary directories"""
    for directory in [config.UPLOADS_DIR, config.FALLBACK_AUDIO_DIR]:
        try:
            directory.mkdir(exist_ok=True)
            logger.info(f"✅ Directory ready: {directory.absolute()}")
        except Exception as e:
            logger.error(f"❌ Error creating directory {directory}: {e}")

setup_directories()

# Initialize services
def initialize_services():
    """Initialize all services and return their status"""
    services = {
        'stt_service': STTService(),
        'llm_service': LLMService(),
        'tts_service': TTSService(),
        'fallback_service': FallbackAudioService(config.FALLBACK_AUDIO_DIR),
        'session_manager': SessionManager()
    }
    
    services_status = ServiceStatus(
        assemblyai=services['stt_service'].is_available(),
        gemini=services['llm_service'].is_available(),
        murf=services['tts_service'].is_available()
    )
    
    logger.info(f"Services initialized - STT: {services_status.assemblyai}, "
                f"LLM: {services_status.gemini}, TTS: {services_status.murf}")
    
    return services, services_status

services, services_status = initialize_services()

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/fallback-audio", StaticFiles(directory="fallback_audio"), name="fallback_audio")

# WebSocket Connection Manager for Audio Streaming
class AudioStreamingManager:
    def __init__(self):
        self.active_connections: Dict[WebSocket, Dict] = {}
        self.audio_buffers: Dict[WebSocket, io.BytesIO] = {}

    async def connect(self, websocket: WebSocket, client_id: str = None):
        await websocket.accept()
        client_id = client_id or f"audio_client_{len(self.active_connections) + 1}"
        
        self.active_connections[websocket] = {
            "client_id": client_id,
            "connected_at": datetime.now().isoformat(),
            "chunks_received": 0,
            "total_bytes": 0,
            "is_recording": False,
            "audio_filename": None
        }
        
        # Initialize audio buffer
        self.audio_buffers[websocket] = io.BytesIO()
        
        logger.info(f"🎤 Audio WebSocket client connected: {client_id}")
        
        # Send welcome message
        await self.send_message(websocket, {
            "type": "connection",
            "message": "Connected to Audio Streaming WebSocket",
            "client_id": client_id,
            "timestamp": datetime.now().isoformat()
        })

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            client_info = self.active_connections[websocket]
            client_id = client_info["client_id"]
            chunks_received = client_info["chunks_received"]
            total_bytes = client_info["total_bytes"]
            
            logger.info(f"🎤 Audio client disconnected: {client_id} "
                       f"(received {chunks_received} chunks, {total_bytes} bytes)")
            
            # Cleanup
            del self.active_connections[websocket]
            if websocket in self.audio_buffers:
                self.audio_buffers[websocket].close()
                del self.audio_buffers[websocket]

    async def send_message(self, websocket: WebSocket, message: dict):
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending WebSocket message: {e}")

    async def handle_audio_chunk(self, websocket: WebSocket, audio_data: bytes):
        """Handle incoming audio chunk"""
        if websocket not in self.active_connections:
            return
        
        client_info = self.active_connections[websocket]
        audio_buffer = self.audio_buffers[websocket]
        
        # Write chunk to buffer
        audio_buffer.write(audio_data)
        
        # Update statistics
        client_info["chunks_received"] += 1
        client_info["total_bytes"] += len(audio_data)
        
        logger.info(f"📦 Received audio chunk from {client_info['client_id']}: "
                   f"chunk #{client_info['chunks_received']}, "
                   f"{len(audio_data)} bytes, "
                   f"total: {client_info['total_bytes']} bytes")
        
        # Send acknowledgment
        await self.send_message(websocket, {
            "type": "chunk_received",
            "chunk_number": client_info["chunks_received"],
            "chunk_size": len(audio_data),
            "total_bytes": client_info["total_bytes"],
            "timestamp": datetime.now().isoformat()
        })

    async def start_recording_session(self, websocket: WebSocket):
        """Start a new recording session"""
        if websocket not in self.active_connections:
            return
        
        client_info = self.active_connections[websocket]
        
        # Reset for new recording
        self.audio_buffers[websocket] = io.BytesIO()
        client_info["chunks_received"] = 0
        client_info["total_bytes"] = 0
        client_info["is_recording"] = True
        
        # Generate filename for this recording session
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        client_info["audio_filename"] = f"streamed_audio_{client_info['client_id']}_{timestamp}.webm"
        
        logger.info(f"🎬 Started recording session for {client_info['client_id']}: {client_info['audio_filename']}")
        
        await self.send_message(websocket, {
            "type": "recording_started",
            "filename": client_info["audio_filename"],
            "timestamp": datetime.now().isoformat()
        })

    async def stop_recording_session(self, websocket: WebSocket):
        """Stop recording session and save audio file"""
        if websocket not in self.active_connections:
            return
        
        client_info = self.active_connections[websocket]
        audio_buffer = self.audio_buffers[websocket]
        
        client_info["is_recording"] = False
        
        # Save audio file
        if client_info["audio_filename"] and audio_buffer.tell() > 0:
            file_path = config.UPLOADS_DIR / client_info["audio_filename"]
            
            # Get audio data from buffer
            audio_data = audio_buffer.getvalue()
            
            # Save to file
            with open(file_path, 'wb') as f:
                f.write(audio_data)
            
            file_size = len(audio_data)
            
            logger.info(f"💾 Saved streamed audio: {file_path} "
                       f"({file_size} bytes, {client_info['chunks_received']} chunks)")
            
            await self.send_message(websocket, {
                "type": "recording_saved",
                "filename": client_info["audio_filename"],
                "file_path": str(file_path),
                "file_size": file_size,
                "chunks_received": client_info["chunks_received"],
                "total_duration_estimate": f"{file_size / 16000:.2f}s",  # Rough estimate
                "timestamp": datetime.now().isoformat()
            })
        else:
            logger.warning(f"No audio data to save for {client_info['client_id']}")
            await self.send_message(websocket, {
                "type": "recording_error",
                "error": "No audio data received",
                "timestamp": datetime.now().isoformat()
            })

audio_manager = AudioStreamingManager()

# WebSocket endpoint for audio streaming
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, client_id: str = None):
    await audio_manager.connect(websocket, client_id)
    try:
        while True:
            # Receive message from client
            message = await websocket.receive()
            
            if message["type"] == "websocket.receive":
                if "text" in message:
                    # Handle text messages (control messages)
                    try:
                        data = json.loads(message["text"])
                        await handle_control_message(websocket, data)
                    except json.JSONDecodeError:
                        # Handle plain text
                        await handle_plain_text_message(websocket, message["text"])
                
                elif "bytes" in message:
                    # Handle binary audio data
                    audio_data = message["bytes"]
                    await audio_manager.handle_audio_chunk(websocket, audio_data)
                    
    except WebSocketDisconnect:
        # Stop any ongoing recording before disconnect
        if websocket in audio_manager.active_connections:
            client_info = audio_manager.active_connections[websocket]
            if client_info.get("is_recording", False):
                await audio_manager.stop_recording_session(websocket)
        audio_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        audio_manager.disconnect(websocket)

async def handle_control_message(websocket: WebSocket, data: dict):
    """Handle control messages (JSON)"""
    message_type = data.get("type", "unknown")
    client_info = audio_manager.active_connections.get(websocket, {})
    
    if message_type == "start_recording":
        await audio_manager.start_recording_session(websocket)
        
    elif message_type == "stop_recording":
        await audio_manager.stop_recording_session(websocket)
        
    elif message_type == "ping":
        await audio_manager.send_message(websocket, {
            "type": "pong",
            "timestamp": datetime.now().isoformat(),
            "client_id": client_info.get("client_id")
        })
        
    elif message_type == "status":
        await audio_manager.send_message(websocket, {
            "type": "status_response",
            "client_info": client_info,
            "is_recording": client_info.get("is_recording", False),
            "chunks_received": client_info.get("chunks_received", 0),
            "total_bytes": client_info.get("total_bytes", 0),
            "timestamp": datetime.now().isoformat()
        })
        
    else:
        await audio_manager.send_message(websocket, {
            "type": "unknown_command",
            "received_type": message_type,
            "available_commands": ["start_recording", "stop_recording", "ping", "status"],
            "timestamp": datetime.now().isoformat()
        })

async def handle_plain_text_message(websocket: WebSocket, text: str):
    """Handle plain text messages"""
    client_info = audio_manager.active_connections.get(websocket, {})
    
    await audio_manager.send_message(websocket, {
        "type": "text_echo",
        "original_message": text,
        "echo": f"Server received: {text}",
        "client_id": client_info.get("client_id"),
        "timestamp": datetime.now().isoformat()
    })

# WebSocket info endpoint
@app.get("/ws/info", response_model=dict)
def websocket_info():
    """Get WebSocket connection information"""
    return {
        "websocket_endpoint": "/ws",
        "connection_stats": {
            "total_connections": len(audio_manager.active_connections),
            "connections": [
                {
                    "client_id": info["client_id"],
                    "connected_at": info["connected_at"],
                    "chunks_received": info["chunks_received"],
                    "total_bytes": info["total_bytes"],
                    "is_recording": info["is_recording"]
                }
                for info in audio_manager.active_connections.values()
            ]
        },
        "supported_message_types": [
            {
                "type": "start_recording",
                "description": "Start audio recording session",
                "example": {"type": "start_recording"}
            },
            {
                "type": "stop_recording", 
                "description": "Stop recording and save audio file",
                "example": {"type": "stop_recording"}
            },
            {
                "type": "ping",
                "description": "Health check ping",
                "example": {"type": "ping"}
            },
            {
                "type": "status",
                "description": "Get current recording status",
                "example": {"type": "status"}
            }
        ],
        "binary_data_support": True,
        "audio_save_location": str(config.UPLOADS_DIR.absolute()),
        "timestamp": datetime.now().isoformat()
    }

# Utility functions (keeping existing ones)
def generate_session_id() -> str:
    """Generate unique session ID"""
    return f"session_{int(datetime.now().timestamp())}"

# API Endpoints (keeping all existing endpoints)
@app.get("/", response_model=dict)
def root():
    """Root endpoint with API status"""
    return {
        "message": "Voice AI Assistant API with Audio Streaming",
        "services_status": services_status.dict(),
        "websocket_endpoint": "/ws",
        "websocket_info": "/ws/info",
        "active_websocket_connections": len(audio_manager.active_connections),
        "streaming_support": True,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health", response_model=HealthResponse)
def health_check():
    """Comprehensive health check endpoint"""
    return HealthResponse(
        status="healthy",
        services=services_status,
        uptime=datetime.now().isoformat(),
        fallback_available=True
    )

# Replace the existing @app.websocket("/ws/streaming-transcribe") endpoint in app.py with this:

@app.websocket("/ws/streaming-transcribe")
async def streaming_transcribe_websocket(websocket: WebSocket):
    """WebSocket endpoint for streaming transcription using latest AssemblyAI SDK"""
    await websocket.accept()
    logger.info("🔗 WebSocket connection established for streaming transcription")
    
    # Create streaming service instance for this session
    streaming_service = StreamingSTTService()
    
    try:
        # Check if service is available
        if not streaming_service.is_available():
            error_msg = {
                "status": "error",
                "message": "AssemblyAI streaming service not available",
                "timestamp": time.time()
            }
            await websocket.send_text(json.dumps(error_msg))
            return

        # Initialize streaming session
        session_created = await streaming_service.create_streaming_session(websocket)
        if not session_created:
            error_msg = {
                "status": "error",
                "message": "Failed to create streaming session",
                "timestamp": time.time()
            }
            await websocket.send_text(json.dumps(error_msg))
            return

        # Send ready message
        ready_msg = {
            "status": "ready",
            "message": "Streaming transcription ready",
            "expected_format": "16kHz, 16-bit, mono PCM",
            "encoding": "base64",
            "api_version": "Latest-SDK",
            "timestamp": time.time()
        }
        await websocket.send_text(json.dumps(ready_msg))

        # Main message handling loop
        while True:
            try:
                # Receive message from client
                message = await websocket.receive_text()
                data = json.loads(message)
                message_type = data.get("type", "unknown")

                if message_type == "audio":
                    # Process audio data
                    audio_base64 = data.get("audio")
                    if audio_base64:
                        try:
                            # Decode base64 to bytes
                            audio_bytes = base64.b64decode(audio_base64)
                            # Send to streaming service
                            success = await streaming_service.send_audio_data(audio_bytes)
                            if not success:
                                logger.warning("⚠️ Failed to send audio data to streaming service")
                        except Exception as e:
                            logger.error(f"❌ Audio processing error: {e}")
                            error_msg = {
                                "status": "error",
                                "error": f"Audio processing failed: {str(e)}",
                                "timestamp": time.time()
                            }
                            await websocket.send_text(json.dumps(error_msg))

                elif message_type == "stop":
                    logger.info("🛑 Client requested stop")
                    break

                elif message_type == "force_endpoint":
                    # Force endpoint detection
                    success = await streaming_service.send_force_endpoint()
                    if success:
                        await websocket.send_text(json.dumps({
                            "status": "force_endpoint_sent",
                            "timestamp": time.time()
                        }))

                elif message_type == "ping":
                    pong_msg = {
                        "status": "pong",
                        "timestamp": data.get("timestamp", time.time())
                    }
                    await websocket.send_text(json.dumps(pong_msg))

                else:
                    logger.warning(f"⚠️ Unknown message type: {message_type}")

            except WebSocketDisconnect:
                logger.info("🔌 Client disconnected from streaming")
                break
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON decode error: {e}")
                error_msg = {
                    "status": "error",
                    "message": "Invalid JSON format",
                    "timestamp": time.time()
                }
                try:
                    await websocket.send_text(json.dumps(error_msg))
                except:
                    pass
            except Exception as e:
                logger.error(f"❌ Error processing message: {e}")
                break

    except Exception as e:
        logger.error(f"❌ Fatal WebSocket error: {e}")
        try:
            error_msg = {
                "status": "fatal_error",
                "message": str(e),
                "timestamp": time.time()
            }
            await websocket.send_text(json.dumps(error_msg))
        except:
            pass

    finally:
        # Cleanup
        try:
            await streaming_service.close_streaming_session()
            logger.info("🔴 Streaming session cleanup completed")
        except Exception as e:
            logger.error(f"❌ Error during cleanup: {e}")

        try:
            if websocket.client_state.name != 'DISCONNECTED':
                await websocket.close()
        except:
            pass
async def process_assemblyai_response(data: dict, websocket: WebSocket):
    """FIXED: Process Universal-Streaming responses"""
    try:
        message_type = data.get("message_type", "")
        
        if message_type == "SessionBegins":
            session_id = data.get("session_id", "")
            logger.info(f"🎙️ Universal-Streaming session opened: {session_id}")
            print(f"🎙️ UNIVERSAL-STREAMING SESSION STARTED: {session_id}")
            await websocket.send_text(json.dumps({
                "status": "session_opened",
                "session_id": session_id
            }))
            
        elif message_type == "Turn":
            # FIXED: Handle Turn messages from Universal-Streaming
            turn_order = data.get("turn_order", 0)
            transcript = data.get("transcript", "")
            end_of_turn = data.get("end_of_turn", False)
            turn_is_formatted = data.get("turn_is_formatted", False)
            words = data.get("words", [])
            
            if transcript:
                # Determine if this is partial or final
                if end_of_turn and turn_is_formatted:
                    message_type_str = "FinalTranscript"
                    print(f"🎯 FINAL TRANSCRIPT (Turn {turn_order}): {transcript}")
                    logger.info(f"🎯 FINAL TRANSCRIPT (Turn {turn_order}): {transcript}")
                else:
                    message_type_str = "PartialTranscript"
                    print(f"🔄 PARTIAL TRANSCRIPT (Turn {turn_order}): {transcript}")
                    logger.info(f"🔄 PARTIAL TRANSCRIPT (Turn {turn_order}): {transcript}")
                
                # Send to client in compatible format
                transcript_data = {
                    "status": "transcript",
                    "text": transcript,
                    "message_type": message_type_str,
                    "turn_order": turn_order,
                    "end_of_turn": end_of_turn,
                    "turn_is_formatted": turn_is_formatted,
                    "confidence": data.get("end_of_turn_confidence", 0.0),
                    "words": words
                }
                
                await websocket.send_text(json.dumps(transcript_data))
        
        elif message_type == "SessionTerminated":
            logger.info("🔚 Universal-Streaming session terminated")
            print("🔚 UNIVERSAL-STREAMING SESSION TERMINATED")
            await websocket.send_text(json.dumps({"status": "session_closed"}))
        
        else:
            # Handle any other message types
            logger.info(f"📨 Unknown message type: {message_type}")
            print(f"📨 UNKNOWN MESSAGE TYPE: {message_type}")
            
    except Exception as e:
        logger.error(f"Error processing AssemblyAI response: {e}")
        await websocket.send_text(json.dumps({
            "status": "error",
            "error": f"Response processing error: {str(e)}"
        }))

async def process_client_message(data: dict, assemblyai_ws):
    """FIXED: Process client messages and forward to Universal-Streaming"""
    try:
        message_type = data.get("type", "unknown")
        
        if message_type == "audio":
            # Process audio data
            audio_base64 = data.get("audio")
            if audio_base64 and assemblyai_ws:
                try:
                    # Decode base64 to bytes
                    audio_bytes = base64.b64decode(audio_base64)
                    
                    # FIXED: Send audio message in Universal-Streaming format
                    audio_message = {
                        "message_type": "AudioData",
                        "audio_data": audio_base64  # Universal-Streaming expects base64
                    }
                    
                    await assemblyai_ws.send(json.dumps(audio_message))
                    logger.debug(f"📦 Sent {len(audio_bytes)} bytes to Universal-Streaming")
                    
                except Exception as e:
                    logger.error(f"❌ Audio processing error: {e}")
                    print(f"❌ AUDIO PROCESSING ERROR: {e}")
        
        elif message_type == "stop":
            logger.info("🛑 Client requested stop")
            print("🛑 CLIENT REQUESTED STOP")
            if assemblyai_ws:
                termination_msg = {"message_type": "TerminateSession"}
                await assemblyai_ws.send(json.dumps(termination_msg))
        
        elif message_type == "force_endpoint":
            # Force end of current turn
            if assemblyai_ws:
                force_endpoint_msg = {"message_type": "ForceEndpoint"}
                await assemblyai_ws.send(json.dumps(force_endpoint_msg))
        
        elif message_type == "ping":
            # Respond to ping (don't forward to AssemblyAI)
            return {"type": "pong", "timestamp": data.get("timestamp")}
            
    except Exception as e:
        logger.error(f"Error processing client message: {e}")


# [All other existing endpoints remain the same...]
# For brevity, I'm showing just the key WebSocket functionality above

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)