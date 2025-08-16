from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

# Request Models
class TTSRequest(BaseModel):
    text: str
    voiceId: str = "en-US-marcus"
    format: str = "MP3"

class LLMRequest(BaseModel):
    text: str

# Response Models
class ServiceStatus(BaseModel):
    assemblyai: bool
    gemini: bool
    murf: bool

class HealthResponse(BaseModel):
    status: str
    services: ServiceStatus
    uptime: str
    fallback_available: bool

class TranscriptionResult(BaseModel):
    success: bool
    text: Optional[str] = None
    duration: Optional[float] = None
    confidence: Optional[float] = None
    error: Optional[str] = None
    fallback_text: Optional[str] = None

class LLMResult(BaseModel):
    success: bool
    text: Optional[str] = None
    error: Optional[str] = None
    fallback_response: Optional[str] = None

class TTSResult(BaseModel):
    success: bool
    audio_url: Optional[str] = None
    error: Optional[str] = None
    fallback_audio: Optional[str] = None
    fallback_text: Optional[str] = None

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: str

class ChatSession(BaseModel):
    messages: List[ChatMessage]
    created_at: str
    last_activity: str

class ConversationResponse(BaseModel):
    status: str
    session_id: Optional[str] = None
    user_query: Optional[str] = None
    ai_response: str
    audioFile: str
    voice_id: str = "en-US-marcus"
    model: str = "gemini-1.5-flash"
    message_count: Optional[int] = None
    audio_duration: Optional[float] = None
    timestamp: str
    service_status: Optional[Dict[str, bool]] = None
    original_filename: Optional[str] = None
    llm_error: Optional[str] = None
    tts_error: Optional[str] = None
    fallback_message: Optional[str] = None
    tts_fallback_message: Optional[str] = None

class AudioUploadResponse(BaseModel):
    message: str
    filename: str
    content_type: str
    size: int

class TranscriptionResponse(BaseModel):
    transcript: Optional[str] = None
    status: str
    filename: Optional[str] = None
    audio_duration: Optional[float] = None
    confidence: Optional[float] = None
    words_count: Optional[int] = None
    error: Optional[str] = None

class TTSResponse(BaseModel):
    status: str
    audio: Optional[Dict[str, str]] = None
    text: Optional[str] = None
    voice_id: Optional[str] = None
    error: Optional[str] = None
    fallback_message: Optional[str] = None

class EchoResponse(BaseModel):
    status: str
    original_filename: Optional[str] = None
    transcribed_text: Optional[str] = None
    audio_url: Optional[str] = None
    voice_id: Optional[str] = None
    audio_duration: Optional[float] = None
    words_count: Optional[int] = None
    error: Optional[str] = None

class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: List[ChatMessage]
    message_count: int
    created_at: Optional[str] = None
    last_activity: Optional[str] = None
    status: str

class FallbackAudioResponse(BaseModel):
    status: str
    message: Optional[str] = None
    audio_url: Optional[str] = None
    download_url: Optional[str] = None
    filename: Optional[str] = None
    file_path: Optional[str] = None
    timestamp: str
    error: Optional[str] = None

class FallbackAudioFile(BaseModel):
    filename: str
    size: int
    created: str
    download_url: str
    play_url: str

class FallbackAudioListResponse(BaseModel):
    status: str
    fallback_audio_files: List[FallbackAudioFile]
    total_files: int
    directory: str
    timestamp: str
    error: Optional[str] = None