from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import logging.config
from pathlib import Path

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

# Utility functions
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

# API Endpoints

@app.get("/", response_model=dict)
def root():
    """Root endpoint with API status"""
    return {
        "message": "Voice AI Assistant API",
        "services_status": services_status.dict(),
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

@app.post("/upload-audio", response_model=AudioUploadResponse)
async def upload_audio(file: UploadFile = File(...)):
    """Upload audio file"""
    try:
        logger.info(f"Received file: {file.filename}, Content-Type: {file.content_type}")
        
        file_path = config.UPLOADS_DIR / file.filename
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        file_size = len(content)
        
        return AudioUploadResponse(
            message="Audio uploaded successfully",
            filename=file.filename,
            content_type=file.content_type,
            size=file_size
        )
    
    except Exception as e:
        logger.error(f"Error uploading audio: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload audio: {str(e)}")

@app.post("/transcribe/file", response_model=TranscriptionResponse)
async def transcribe_file(file: UploadFile = File(...)):
    """Transcribe audio file"""
    try:
        logger.info(f"Received file for transcription: {file.filename}")
        
        audio_data = await file.read()
        logger.info(f"Audio data size: {len(audio_data)} bytes")
        
        transcription_result = await services['stt_service'].transcribe(audio_data)
        
        if not transcription_result.success:
            return TranscriptionResponse(
                error=transcription_result.error,
                status="error"
            )
        
        return TranscriptionResponse(
            transcript=transcription_result.text,
            status="completed",
            filename=file.filename,
            audio_duration=transcription_result.duration,
            confidence=transcription_result.confidence,
            words_count=len(transcription_result.text.split()) if transcription_result.text else 0
        )
        
    except Exception as e:
        logger.error(f"Error during transcription: {e}")
        return TranscriptionResponse(
            error=f"Transcription error: {str(e)}",
            status="error"
        )

@app.post("/generate-audio", response_model=TTSResponse)
async def generate_audio(req: TTSRequest):
    """Generate audio with comprehensive error handling"""
    try:
        logger.info(f"Generating audio for text: {req.text[:50]}...")
        
        if not req.text or req.text.strip() == "":
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        tts_result = await services['tts_service'].generate(req.text, req.voiceId)
        
        if tts_result.success:
            return TTSResponse(
                status="success",
                audio={"audioFile": tts_result.audio_url},
                text=req.text,
                voice_id=req.voiceId
            )
        else:
            logger.warning(f"TTS failed, using fallback: {tts_result.error}")
            fallback_message = services['fallback_service'].get_fallback_message("tts_error")
            fallback_audio = await services['fallback_service'].generate_fallback_audio_url(fallback_message)
            return TTSResponse(
                status="fallback",
                audio={"audioFile": fallback_audio},
                text=req.text,
                voice_id=req.voiceId,
                error=tts_result.error,
                fallback_message=fallback_message
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generate_audio: {e}")
        fallback_message = services['fallback_service'].get_fallback_message("general_error")
        return TTSResponse(
            status="error",
            error=str(e),
            fallback_message=fallback_message
        )

@app.post("/tts/echo", response_model=EchoResponse)
async def tts_echo(file: UploadFile = File(...)):
    """Echo bot - transcribe then speak back"""
    try:
        logger.info(f"Received file for echo: {file.filename}")
        
        audio_data = await file.read()
        logger.info(f"Audio data size: {len(audio_data)} bytes")
        
        # Transcribe
        transcription_result = await services['stt_service'].transcribe(audio_data)
        
        if not transcription_result.success:
            return EchoResponse(
                error=transcription_result.error,
                status="error"
            )
        
        transcribed_text = transcription_result.text
        logger.info(f"Transcription completed: {transcribed_text}")
        
        if not transcribed_text or transcribed_text.strip() == "":
            return EchoResponse(
                error="No speech detected in the audio",
                status="error"
            )
        
        # Generate speech
        tts_result = await services['tts_service'].generate(transcribed_text)
        
        if not tts_result.success:
            return EchoResponse(
                error=f"Speech generation failed: {tts_result.error}",
                status="error"
            )
        
        return EchoResponse(
            status="success",
            original_filename=file.filename,
            transcribed_text=transcribed_text,
            audio_url=tts_result.audio_url,
            voice_id=config.DEFAULT_VOICE_ID,
            audio_duration=transcription_result.duration,
            words_count=len(transcribed_text.split()) if transcribed_text else 0
        )
        
    except Exception as e:
        logger.error(f"Error in echo bot: {e}")
        return EchoResponse(
            error=f"Echo bot error: {str(e)}",
            status="error"
        )

@app.post("/llm/query", response_model=ConversationResponse)
async def llm_query(file: UploadFile = File(...)):
    """Voice LLM query with comprehensive error handling and fallbacks"""
    try:
        logger.info(f"Received audio for LLM query: {file.filename}")
        
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        audio_data = await file.read()
        logger.info(f"Audio data size: {len(audio_data)} bytes")
        
        if len(audio_data) == 0:
            raise HTTPException(status_code=400, detail="Empty audio file")
        
        # Step 1: Transcribe
        logger.info("Step 1: Transcribing audio...")
        transcription_result = await services['stt_service'].transcribe(audio_data)
        
        if not transcription_result.success:
            fallback_message = services['fallback_service'].get_fallback_message("stt_error")
            fallback_audio = await services['fallback_service'].generate_fallback_audio_url(fallback_message)
            return ConversationResponse(
                status="error",
                ai_response=fallback_message,
                audioFile=fallback_audio,
                timestamp=datetime.now().isoformat(),
                original_filename=file.filename
            )
        
        user_query = transcription_result.text
        logger.info(f"User query: {user_query}")
        
        if not user_query or user_query.strip() == "":
            fallback_message = services['fallback_service'].get_fallback_message("stt_error")
            fallback_audio = await services['fallback_service'].generate_fallback_audio_url(fallback_message)
            return ConversationResponse(
                status="error",
                ai_response=fallback_message,
                audioFile=fallback_audio,
                timestamp=datetime.now().isoformat(),
                original_filename=file.filename
            )
        
        # Step 2: Generate AI response
        logger.info("Step 2: Generating LLM response...")
        llm_result = await services['llm_service'].generate(user_query)
        
        if not llm_result.success:
            ai_response_text = llm_result.fallback_response
            llm_success = False
        else:
            ai_response_text = llm_result.text
            llm_success = True
        
        logger.info(f"AI response: {ai_response_text[:100]}...")
        
        # Step 3: Convert to speech
        logger.info("Step 3: Converting AI response to speech...")
        tts_result = await services['tts_service'].generate(ai_response_text)
        
        if tts_result.success:
            audio_url = tts_result.audio_url
            tts_success = True
        else:
            logger.info("TTS failed, generating fallback audio")
            fallback_message = services['fallback_service'].get_fallback_message("tts_error")
            audio_url = await services['fallback_service'].generate_fallback_audio_url(fallback_message)
            tts_success = False
        
        # Determine overall status
        if transcription_result.success and llm_success and tts_success:
            status = "success"
        elif transcription_result.success:
            status = "partial_success"
        else:
            status = "fallback"
        
        logger.info(f"Voice LLM query completed with status: {status}")
        
        response_data = ConversationResponse(
            status=status,
            user_query=user_query,
            ai_response=ai_response_text,
            audioFile=audio_url,
            voice_id=config.DEFAULT_VOICE_ID,
            model=config.DEFAULT_LLM_MODEL,
            audio_duration=transcription_result.duration,
            timestamp=datetime.now().isoformat(),
            service_status={
                "transcription": transcription_result.success,
                "llm": llm_success,
                "tts": tts_success
            },
            original_filename=file.filename
        )
        
        if not llm_success:
            response_data.llm_error = llm_result.error
            response_data.fallback_message = llm_result.fallback_response
        
        if not tts_success:
            response_data.tts_error = tts_result.error
            response_data.tts_fallback_message = tts_result.fallback_text
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in voice LLM query: {e}")
        fallback_message = services['fallback_service'].get_fallback_message("general_error")
        fallback_audio = await services['fallback_service'].generate_fallback_audio_url(fallback_message)
        return ConversationResponse(
            status="error",
            ai_response=fallback_message,
            audioFile=fallback_audio,
            timestamp=datetime.now().isoformat(),
            original_filename=getattr(file, 'filename', 'unknown')
        )

@app.post("/conversation/query", response_model=ConversationResponse)
async def conversation_query(file: UploadFile = File(...), session_id: str = None):
    """Conversational agent endpoint with session management"""
    try:
        logger.info(f"Received conversation query: {file.filename}, Session: {session_id}")
        
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        audio_data = await file.read()
        logger.info(f"Audio data size: {len(audio_data)} bytes")
        
        if len(audio_data) == 0:
            raise HTTPException(status_code=400, detail="Empty audio file")
        
        # Generate session ID if not provided
        if not session_id:
            session_id = generate_session_id()
        
        # Step 1: Transcribe
        logger.info("Step 1: Transcribing audio...")
        transcription_result = await services['stt_service'].transcribe(audio_data)
        
        if not transcription_result.success:
            fallback_message = services['fallback_service'].get_fallback_message("stt_error")
            fallback_audio = await services['fallback_service'].generate_fallback_audio_url(fallback_message)
            return ConversationResponse(
                status="error",
                session_id=session_id,
                ai_response=fallback_message,
                audioFile=fallback_audio,
                timestamp=datetime.now().isoformat()
            )
        
        user_query = transcription_result.text
        logger.info(f"User query: {user_query}")
        
        if not user_query or user_query.strip() == "":
            fallback_message = "I didn't catch that. Could you please repeat?"
            fallback_audio = await services['fallback_service'].generate_fallback_audio_url(fallback_message)
            return ConversationResponse(
                status="error",
                session_id=session_id,
                ai_response=fallback_message,
                audioFile=fallback_audio,
                timestamp=datetime.now().isoformat()
            )
        
        # Add user message to session
        services['session_manager'].add_message(session_id, "user", user_query)
        
        # Step 2: Generate AI response with context
        logger.info("Step 2: Generating AI response with conversation context...")
        
        prompt = create_llm_prompt(user_query, session_id)
        llm_result = await services['llm_service'].generate(prompt)
        
        if not llm_result.success:
            ai_response_text = llm_result.fallback_response
            llm_success = False
        else:
            ai_response_text = llm_result.text
            llm_success = True
        
        # Add AI response to session
        services['session_manager'].add_message(session_id, "assistant", ai_response_text)
        
        logger.info(f"AI response: {ai_response_text[:100]}...")
        
        # Step 3: Convert to speech
        logger.info("Step 3: Converting AI response to speech...")
        tts_result = await services['tts_service'].generate(ai_response_text)
        
        if tts_result.success:
            audio_url = tts_result.audio_url
            tts_success = True
        else:
            logger.info("TTS failed, generating fallback audio")
            audio_url = await services['fallback_service'].generate_fallback_audio_url(ai_response_text)
            tts_success = False
        
        # Determine status
        if transcription_result.success and llm_success and tts_success:
            status = "success"
        elif transcription_result.success:
            status = "partial_success"
        else:
            status = "fallback"
        
        logger.info(f"Conversation query completed with status: {status}")
        
        response_data = ConversationResponse(
            status=status,
            session_id=session_id,
            user_query=user_query,
            ai_response=ai_response_text,
            audioFile=audio_url,
            voice_id=config.DEFAULT_VOICE_ID,
            model=config.DEFAULT_LLM_MODEL,
            message_count=services['session_manager'].get_message_count(session_id),
            audio_duration=transcription_result.duration,
            timestamp=datetime.now().isoformat(),
            service_status={
                "transcription": transcription_result.success,
                "llm": llm_success,
                "tts": tts_success
            }
        )
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in conversation query: {e}")
        fallback_message = services['fallback_service'].get_fallback_message("general_error")
        fallback_audio = await services['fallback_service'].generate_fallback_audio_url(fallback_message)
        return ConversationResponse(
            status="error",
            session_id=session_id,
            ai_response=fallback_message,
            audioFile=fallback_audio,
            timestamp=datetime.now().isoformat()
        )

@app.post("/agent/chat/{session_id}", response_model=ConversationResponse)
async def conversational_agent(session_id: str, file: UploadFile = File(...)):
    """Legacy conversational agent endpoint (redirects to conversation_query)"""
    return await conversation_query(file, session_id)

@app.get("/agent/chat/{session_id}/history", response_model=ChatHistoryResponse)
async def get_chat_history(session_id: str):
    """Get chat history for a session"""
    try:
        session_info = services['session_manager'].get_session_info(session_id)
        
        return ChatHistoryResponse(
            session_id=session_info["session_id"],
            messages=[ChatMessage(**msg) for msg in session_info["messages"]],
            message_count=session_info["message_count"],
            created_at=session_info.get("created_at"),
            last_activity=session_info.get("last_activity"),
            status=session_info["status"]
        )
        
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        raise HTTPException(status_code=500, detail=f"Chat history error: {str(e)}")

# Fallback audio endpoints
@app.get("/generate-fallback-audio/{message}", response_model=FallbackAudioResponse)
async def generate_fallback_audio_endpoint(message: str):
    """Generate and return fallback audio file for a specific message"""
    try:
        logger.info(f"Generating fallback audio for message: {message}")
        
        audio_url = await services['fallback_service'].generate_fallback_audio_url(message)
        
        filename = audio_url.split('/')[-1] if '/' in audio_url else None
        file_path = config.FALLBACK_AUDIO_DIR / filename if filename else None
        
        return FallbackAudioResponse(
            status="success",
            message=f"Fallback audio generated for: {message}",
            audio_url=audio_url,
            download_url=audio_url,
            filename=filename,
            file_path=str(file_path) if file_path else None,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Failed to generate fallback audio: {e}")
        return FallbackAudioResponse(
            status="error",
            error=str(e),
            timestamp=datetime.now().isoformat()
        )

@app.get("/download-fallback-audio/{filename}")
async def download_fallback_audio(filename: str):
    """Download a specific fallback audio file"""
    try:
        file_path = config.FALLBACK_AUDIO_DIR / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Fallback audio file not found")
        
        return FileResponse(
            path=str(file_path),
            media_type="audio/mpeg",
            filename=filename,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Failed to download fallback audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/list-fallback-audio", response_model=FallbackAudioListResponse)
async def list_fallback_audio():
    """List all available fallback audio files"""
    try:
        audio_files = []
        
        if config.FALLBACK_AUDIO_DIR.exists():
            for file_path in config.FALLBACK_AUDIO_DIR.glob("*.mp3"):
                file_stats = file_path.stat()
                audio_files.append(FallbackAudioFile(
                    filename=file_path.name,
                    size=file_stats.st_size,
                    created=datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
                    download_url=f"http://localhost:8000/download-fallback-audio/{file_path.name}",
                    play_url=f"http://localhost:8000/fallback-audio/{file_path.name}"
                ))
        
        return FallbackAudioListResponse(
            status="success",
            fallback_audio_files=audio_files,
            total_files=len(audio_files),
            directory=str(config.FALLBACK_AUDIO_DIR.absolute()),
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Failed to list fallback audio files: {e}")
        return FallbackAudioListResponse(
            status="error",
            fallback_audio_files=[],
            total_files=0,
            directory=str(config.FALLBACK_AUDIO_DIR.absolute()),
            timestamp=datetime.now().isoformat(),
            error=str(e)
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)