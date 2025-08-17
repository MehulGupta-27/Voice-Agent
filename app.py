# Updated app.py with WebSocket support

from fastapi import FastAPI, File, UploadFile, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import logging.config
from pathlib import Path
import json
from typing import List, Dict

# Import configurations and schemas
import config
from schemas import *

# Import services
from services.stt_service import STTService
from services.llm_service import LLMService
from services.tts_service import TTSService
from services.fallback_service import FallbackAudioService
from services.session_manager import SessionManager

# Configure logging
logging.config.dictConfig(config.LOGGING_CONFIG)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Voice AI Assistant", version="1.0.0")

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

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_info: Dict[WebSocket, Dict] = {}

    async def connect(self, websocket: WebSocket, client_id: str = None):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_info[websocket] = {
            "client_id": client_id or f"client_{len(self.active_connections)}",
            "connected_at": datetime.now().isoformat(),
            "message_count": 0
        }
        logger.info(f"WebSocket client connected: {self.connection_info[websocket]['client_id']}")
        
        # Send welcome message
        await self.send_personal_message({
            "type": "connection",
            "message": "Connected to Voice AI Assistant WebSocket",
            "client_id": self.connection_info[websocket]['client_id'],
            "timestamp": datetime.now().isoformat(),
            "total_connections": len(self.active_connections)
        }, websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            client_info = self.connection_info.get(websocket, {})
            client_id = client_info.get("client_id", "unknown")
            message_count = client_info.get("message_count", 0)
            
            self.active_connections.remove(websocket)
            if websocket in self.connection_info:
                del self.connection_info[websocket]
            
            logger.info(f"WebSocket client disconnected: {client_id} (sent {message_count} messages)")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_text(json.dumps(message, indent=2))
            if websocket in self.connection_info:
                self.connection_info[websocket]["message_count"] += 1
        except Exception as e:
            logger.error(f"Error sending message to WebSocket: {e}")

    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message, indent=2))
                if connection in self.connection_info:
                    self.connection_info[connection]["message_count"] += 1
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

    def get_connection_stats(self):
        return {
            "total_connections": len(self.active_connections),
            "connections": [
                {
                    "client_id": info["client_id"],
                    "connected_at": info["connected_at"],
                    "message_count": info["message_count"]
                }
                for info in self.connection_info.values()
            ]
        }

manager = ConnectionManager()

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, client_id: str = None):
    await manager.connect(websocket, client_id)
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            logger.info(f"Received WebSocket message: {data}")
            
            try:
                # Try to parse as JSON
                message_data = json.loads(data)
                message_type = message_data.get("type", "message")
                message_content = message_data.get("message", data)
                client_info = manager.connection_info.get(websocket, {})
                
                # Create response based on message type
                if message_type == "ping":
                    response = {
                        "type": "pong",
                        "message": "pong",
                        "timestamp": datetime.now().isoformat(),
                        "client_id": client_info.get("client_id")
                    }
                elif message_type == "echo":
                    response = {
                        "type": "echo_response",
                        "original_message": message_content,
                        "echo": f"Echo: {message_content}",
                        "timestamp": datetime.now().isoformat(),
                        "client_id": client_info.get("client_id")
                    }
                elif message_type == "stats":
                    response = {
                        "type": "stats_response",
                        "connection_stats": manager.get_connection_stats(),
                        "services_status": services_status.dict(),
                        "timestamp": datetime.now().isoformat()
                    }
                elif message_type == "broadcast":
                    # Broadcast message to all connected clients
                    broadcast_msg = {
                        "type": "broadcast",
                        "message": message_content,
                        "from_client": client_info.get("client_id"),
                        "timestamp": datetime.now().isoformat()
                    }
                    await manager.broadcast(broadcast_msg)
                    continue  # Don't send individual response
                else:
                    # Default echo behavior
                    response = {
                        "type": "echo",
                        "original_message": message_data,
                        "echo": f"Server received: {message_content}",
                        "message_count": client_info.get("message_count", 0) + 1,
                        "timestamp": datetime.now().isoformat(),
                        "client_id": client_info.get("client_id")
                    }
                    
            except json.JSONDecodeError:
                # Handle plain text messages
                client_info = manager.connection_info.get(websocket, {})
                response = {
                    "type": "text_echo",
                    "original_message": data,
                    "echo": f"Server received: {data}",
                    "message_count": client_info.get("message_count", 0) + 1,
                    "timestamp": datetime.now().isoformat(),
                    "client_id": client_info.get("client_id")
                }
            
            # Send response back to client
            await manager.send_personal_message(response, websocket)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# WebSocket info endpoint
@app.get("/ws/info", response_model=dict)
def websocket_info():
    """Get WebSocket connection information"""
    return {
        "websocket_endpoint": "/ws",
        "connection_stats": manager.get_connection_stats(),
        "supported_message_types": [
            {
                "type": "ping",
                "description": "Send ping, receive pong",
                "example": {"type": "ping"}
            },
            {
                "type": "echo",
                "description": "Echo a specific message",
                "example": {"type": "echo", "message": "Hello WebSocket!"}
            },
            {
                "type": "stats",
                "description": "Get connection and service statistics",
                "example": {"type": "stats"}
            },
            {
                "type": "broadcast",
                "description": "Broadcast message to all connected clients",
                "example": {"type": "broadcast", "message": "Hello everyone!"}
            },
            {
                "type": "message",
                "description": "Send a regular message (default behavior)",
                "example": {"type": "message", "message": "Hello!"}
            }
        ],
        "plain_text_support": True,
        "timestamp": datetime.now().isoformat()
    }

# Utility functions (keeping existing ones)
def generate_session_id() -> str:
    """Generate unique session ID"""
    return f"session_{int(datetime.now().timestamp())}"

def create_llm_prompt(user_query: str, session_id: str) -> str:
    """Create prompt with conversation context"""
    conversation_context = services['session_manager'].get_conversation_context(session_id)
    
    if conversation_context:
        return f"""You are a helpful AI assistant having a natural conversation. 

Previous conversation:
{conversation_context}

Please respond naturally and conversationally to the user's latest message. Keep your response concise but helpful."""
    else:
        return f"""You are a helpful and friendly AI assistant having a natural conversation. Keep your responses conversational and engaging.

User: {user_query}

Please respond to the user's message naturally."""

# Keep all existing API endpoints...
@app.get("/", response_model=dict)
def root():
    """Root endpoint with API status"""
    return {
        "message": "Voice AI Assistant API with WebSocket Support",
        "services_status": services_status.dict(),
        "websocket_endpoint": "/ws",
        "websocket_info": "/ws/info",
        "active_websocket_connections": len(manager.active_connections),
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

# [Keep all other existing endpoints from the original app.py - they remain unchanged]
# For brevity, I'm not duplicating all the existing endpoints here, but they should all remain

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)