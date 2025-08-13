from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import requests
from pathlib import Path
import assemblyai as aai
import google.generativeai as genai
from datetime import datetime

import logging
import time
from typing import Optional
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


load_dotenv()

app = FastAPI()

uploads_dir = Path("uploads")
fallback_audio_dir = Path("fallback_audio")

try:
    uploads_dir.mkdir(exist_ok=True)
    logger.info(f"✅ Uploads directory ready: {uploads_dir.absolute()}")
except Exception as e:
    logger.error(f"❌ Error creating uploads directory: {e}")
    uploads_dir = Path(".")

try:
    fallback_audio_dir.mkdir(exist_ok=True)
    logger.info(f"✅ Fallback audio directory ready: {fallback_audio_dir.absolute()}")
except Exception as e:
    logger.error(f"❌ Error creating fallback audio directory: {e}")
    fallback_audio_dir = Path(".")

def initialize_services():
    """Initialize all API services with proper error handling"""
    services_status = {
        "assemblyai": False,
        "gemini": False,
        "murf": False
    }
    
    try:
        assemblyai_key = os.getenv("ASSEMBLYAI_API_KEY")
        if not assemblyai_key:
            logger.error("❌ AssemblyAI API key not found")
        else:
            aai.settings.api_key = assemblyai_key
            global transcriber
            transcriber = aai.Transcriber()
            services_status["assemblyai"] = True
            logger.info("✅ AssemblyAI initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize AssemblyAI: {e}")
    
    try:
        gemini_key = os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            logger.error("❌ Gemini API key not found")
        else:
            genai.configure(api_key=gemini_key)
            global gemini_model
            gemini_model = genai.GenerativeModel('gemini-1.5-flash')
            services_status["gemini"] = True
            logger.info("✅ Gemini AI initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Gemini: {e}")
    
    try:
        murf_key = os.getenv("MURF_API_KEY")
        if not murf_key:
            logger.error("❌ Murf API key not found")
        else:
            services_status["murf"] = True
            logger.info("✅ Murf API key found")
    except Exception as e:
        logger.error(f"❌ Failed to check Murf API key: {e}")
    
    return services_status

services_status = initialize_services()
chat_sessions = {}

FALLBACK_RESPONSES = {
    "stt_error": "I'm having trouble understanding your audio right now. Please try speaking more clearly or check your microphone.",
    "llm_error": "I'm having trouble connecting right now. My AI brain needs a moment to reboot. Please try again in a few seconds.",
    "tts_error": "I'm having trouble connecting right now. I can understand you, but I'm having trouble speaking right now.",
    "network_error": "I'm having trouble connecting right now. Please check your internet connection and try again.",
    "general_error": "I'm having trouble connecting right now. Something unexpected happened. Please try again in a moment."
}

async def generate_fallback_audio_url(text: str) -> str:
    """Generate fallback audio using same voice as main TTS (Murf), with gTTS backup"""
    try:
        import hashlib
        
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        murf_filename = f"murf_fallback_{text_hash}.mp3"
        murf_file_path = fallback_audio_dir / murf_filename
        
        if murf_file_path.exists():
            logger.info(f"Using existing Murf fallback audio: {murf_filename}")
            return f"http://localhost:8000/fallback-audio/{murf_filename}"
        
        logger.info(f"Generating fallback audio using Murf API (same voice as main TTS) for: '{text[:50]}...'")
        
        murf_result = await generate_murf_fallback_audio(text, murf_file_path)
        if murf_result:
            logger.info(f"✅ Murf fallback audio saved: {murf_file_path}")
            return f"http://localhost:8000/fallback-audio/{murf_filename}"
        
        logger.warning("Murf API failed for fallback, using gTTS with faster speed")
        return await generate_gtts_fallback_audio(text)
        
    except Exception as e:
        logger.error(f"Failed to generate fallback audio: {e}")
        return create_web_speech_fallback(text)

async def generate_murf_fallback_audio(text: str, file_path: Path) -> bool:
    """Generate fallback audio using Murf API (same voice as main TTS)"""
    try:
        import requests
        
        url = "https://api.murf.ai/v1/speech/generate-with-key"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "api-key": os.getenv("MURF_API_KEY")
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

async def generate_gtts_fallback_audio(text: str) -> str:
    """Generate fallback audio using gTTS with faster speed and better settings"""
    try:
        from gtts import gTTS
        import hashlib
        
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        filename = f"gtts_fallback_{text_hash}.mp3"
        file_path = fallback_audio_dir / filename
        
        if file_path.exists():
            logger.info(f"Using existing gTTS fallback audio: {filename}")
            return f"http://localhost:8000/fallback-audio/{filename}"
        
        logger.info("Generating gTTS fallback with optimized settings...")
        
        tts = gTTS(
            text=text, 
            lang='en', 
            slow=False,
            tld='com'
        )
        tts.save(str(file_path))
        
        logger.info(f"✅ gTTS fallback audio saved: {file_path}")
        return f"http://localhost:8000/fallback-audio/{filename}"
        
    except ImportError:
        logger.warning("gTTS not available, using Web Speech API fallback")
        return create_web_speech_fallback(text)
    except Exception as e:
        logger.error(f"gTTS fallback generation failed: {e}")
        return create_web_speech_fallback(text)

def create_web_speech_fallback(text: str) -> str:
    """Create a fallback that uses browser's Web Speech API"""
    logger.info("Using Web Speech API fallback")
    
    import base64
    
    text_base64 = base64.b64encode(text.encode('utf-8')).decode('utf-8')
    
    return f"web-speech:{text_base64}"

async def safe_transcribe(audio_data: bytes, max_retries: int = 3) -> dict:
    """Safely transcribe audio with retries and fallback"""
    if not services_status["assemblyai"]:
        return {
            "success": False,
            "error": "AssemblyAI service not available",
            "fallback_text": "Speech transcription unavailable"
        }
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Transcription attempt {attempt + 1}/{max_retries}")
            transcript = transcriber.transcribe(audio_data)
            
            if transcript.status == aai.TranscriptStatus.error:
                logger.error(f"Transcription failed: {transcript.error}")
                if attempt == max_retries - 1:
                    return {
                        "success": False,
                        "error": f"Transcription failed: {transcript.error}",
                        "fallback_text": "Could not transcribe audio"
                    }
                continue
            
            return {
                "success": True,
                "text": transcript.text,
                "duration": transcript.audio_duration,
                "confidence": getattr(transcript, 'confidence', None)
            }
            
        except Exception as e:
            logger.error(f"Transcription attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                return {
                    "success": False,
                    "error": str(e),
                    "fallback_text": "Transcription service error"
                }
            time.sleep(1)
    
    return {
        "success": False,
        "error": "Max retries exceeded",
        "fallback_text": "Could not process audio"
    }

async def safe_llm_generate(prompt: str, max_retries: int = 3) -> dict:
    """Safely generate LLM response with retries and fallback"""
    if not services_status["gemini"]:
        return {
            "success": False,
            "error": "Gemini AI service not available",
            "fallback_response": FALLBACK_RESPONSES["llm_error"]
        }
    
    for attempt in range(max_retries):
        try:
            logger.info(f"LLM generation attempt {attempt + 1}/{max_retries}")
            response = gemini_model.generate_content(prompt)
            
            if not response.text:
                if attempt == max_retries - 1:
                    return {
                        "success": False,
                        "error": "No response generated",
                        "fallback_response": FALLBACK_RESPONSES["llm_error"]
                    }
                continue
            
            return {
                "success": True,
                "text": response.text.strip()
            }
            
        except Exception as e:
            logger.error(f"LLM generation attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                return {
                    "success": False,
                    "error": str(e),
                    "fallback_response": FALLBACK_RESPONSES["llm_error"]
                }
            time.sleep(2)
    
    return {
        "success": False,
        "error": "Max retries exceeded",
        "fallback_response": FALLBACK_RESPONSES["llm_error"]
    }

async def safe_tts_generate(text: str, voice_id: str = "en-US-marcus", max_retries: int = 3) -> dict:
    """Safely generate TTS audio with retries and fallback"""
    if not services_status["murf"]:
        fallback_message = "I'm having trouble connecting right now"
        fallback_audio = await generate_fallback_audio_url(fallback_message)
        return {
            "success": False,
            "error": "Murf TTS service not available",
            "fallback_audio": fallback_audio,
            "fallback_text": fallback_message
        }
    
    for attempt in range(max_retries):
        try:
            logger.info(f"TTS generation attempt {attempt + 1}/{max_retries}")
            
            url = "https://api.murf.ai/v1/speech/generate-with-key"
            headers = {
                "accept": "application/json",
                "Content-Type": "application/json",
                "api-key": os.getenv("MURF_API_KEY")
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
                    fallback_message = "I'm having trouble connecting right now"
                    fallback_audio = await generate_fallback_audio_url(fallback_message)
                    return {
                        "success": False,
                        "error": f"TTS API failed: {response.status_code}",
                        "fallback_audio": fallback_audio,
                        "fallback_text": fallback_message
                    }
                continue
            
            result = response.json()
            audio_url = result.get("audioFile")
            
            if not audio_url:
                if attempt == max_retries - 1:
                    fallback_message = "I'm having trouble connecting right now"
                    fallback_audio = await generate_fallback_audio_url(fallback_message)
                    return {
                        "success": False,
                        "error": "No audio URL received",
                        "fallback_audio": fallback_audio,
                        "fallback_text": fallback_message
                    }
                continue
            
            return {
                "success": True,
                "audio_url": audio_url
            }
            
        except Exception as e:
            logger.error(f"TTS generation attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                fallback_message = "I'm having trouble connecting right now"
                fallback_audio = await generate_fallback_audio_url(fallback_message)
                return {
                    "success": False,
                    "error": str(e),
                    "fallback_audio": fallback_audio,
                    "fallback_text": fallback_message
                }
            time.sleep(1)
    
    fallback_message = "I'm having trouble connecting right now"
    fallback_audio = await generate_fallback_audio_url(fallback_message)
    return {
        "success": False,
        "error": "Max retries exceeded",
        "fallback_audio": fallback_audio,
        "fallback_text": fallback_message
    }
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/fallback-audio", StaticFiles(directory="fallback_audio"), name="fallback_audio")

class TTSRequest(BaseModel):
    text: str
    voiceId: str
    format: str = "MP3"

class LLMRequest(BaseModel):
    text: str

@app.get("/")
def working():
    return {
        "message": "API working good",
        "services_status": services_status,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
def health_check():
    """Comprehensive health check endpoint"""
    return {
        "status": "healthy",
        "services": services_status,
        "uptime": datetime.now().isoformat(),
        "fallback_available": True
    }



@app.get("/generate-fallback-audio/{message}")
async def generate_fallback_audio_endpoint(message: str):
    """Generate and return fallback audio file for a specific message"""
    try:
        logger.info(f"Generating fallback audio for message: {message}")
        
        audio_url = await generate_fallback_audio_url(message)
        
        filename = audio_url.split('/')[-1] if '/' in audio_url else None
        file_path = fallback_audio_dir / filename if filename else None
        
        return {
            "status": "success",
            "message": f"Fallback audio generated for: {message}",
            "audio_url": audio_url,
            "download_url": audio_url,
            "filename": filename,
            "file_path": str(file_path) if file_path else None,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to generate fallback audio: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/download-fallback-audio/{filename}")
async def download_fallback_audio(filename: str):
    """Download a specific fallback audio file"""
    try:
        file_path = fallback_audio_dir / filename
        
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

@app.get("/list-fallback-audio")
async def list_fallback_audio():
    """List all available fallback audio files"""
    try:
        audio_files = []
        
        if fallback_audio_dir.exists():
            for file_path in fallback_audio_dir.glob("*.mp3"):
                file_stats = file_path.stat()
                audio_files.append({
                    "filename": file_path.name,
                    "size": file_stats.st_size,
                    "created": datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
                    "download_url": f"http://localhost:8000/download-fallback-audio/{file_path.name}",
                    "play_url": f"http://localhost:8000/fallback-audio/{file_path.name}"
                })
        
        return {
            "status": "success",
            "fallback_audio_files": audio_files,
            "total_files": len(audio_files),
            "directory": str(fallback_audio_dir.absolute()),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to list fallback audio files: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }



@app.post("/generate-audio")
async def generate_audio(req: TTSRequest):
    """Generate audio with comprehensive error handling"""
    try:
        logger.info(f"Generating audio for text: {req.text[:50]}...")
        
        if not req.text or req.text.strip() == "":
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        tts_result = await safe_tts_generate(req.text, req.voiceId)
        
        if tts_result["success"]:
            return {
                "status": "success",
                "audio": {
                    "audioFile": tts_result["audio_url"]
                },
                "text": req.text,
                "voice_id": req.voiceId
            }
        else:
            logger.warning(f"TTS failed, using fallback: {tts_result['error']}")
            fallback_message = "I'm having trouble connecting right now"
            fallback_audio = await generate_fallback_audio_url(fallback_message)
            return {
                "status": "fallback",
                "audio": {
                    "audioFile": fallback_audio
                },
                "text": req.text,
                "voice_id": req.voiceId,
                "error": tts_result["error"],
                "fallback_message": fallback_message
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generate_audio: {e}")
        return {
            "status": "error",
            "error": str(e),
            "fallback_message": FALLBACK_RESPONSES["general_error"]
        }

@app.post("/upload-audio")
async def upload_audio(file: UploadFile = File(...)):
    try:
        print(f"Received file: {file.filename}, Content-Type: {file.content_type}")
        
        file_path = uploads_dir / file.filename
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        file_size = len(content)
        
        response_data = {
            "message": "Audio uploaded successfully",
            "filename": file.filename,
            "content_type": file.content_type,
            "size": file_size
        }
        
        print(f"Returning response: {response_data}")
        return response_data
    
    except Exception as e:
        error_response = {"error": f"Failed to upload audio: {str(e)}"}
        print(f"Error occurred: {error_response}")
        return error_response

@app.post("/transcribe/file")
async def transcribe_file(file: UploadFile = File(...)):
    try:
        print(f"Received file for transcription: {file.filename}, Content-Type: {file.content_type}")
        
        audio_data = await file.read()
        print(f"Audio data size: {len(audio_data)} bytes")
        
        print("Starting transcription with AssemblyAI...")
        transcript = transcriber.transcribe(audio_data)
        
        if transcript.status == aai.TranscriptStatus.error:
            print(f"Transcription failed: {transcript.error}")
            return {
                "error": f"Transcription failed: {transcript.error}",
                "status": "error"
            }
        
        print(f"Transcription completed successfully")
        print(f"Transcript text: {transcript.text[:100]}...")
        
        response_data = {
            "transcript": transcript.text,
            "status": "completed",
            "filename": file.filename,
            "audio_duration": transcript.audio_duration,
            "confidence": getattr(transcript, 'confidence', None),
            "words_count": len(transcript.text.split()) if transcript.text else 0
        }
        
        return response_data
        
    except Exception as e:
        print(f"Error during transcription: {str(e)}")
        return {
            "error": f"Transcription error: {str(e)}",
            "status": "error"
        }
        
@app.post("/tts/echo")
async def tts_echo(file: UploadFile = File(...)):
    try:
        print(f"Received file for echo: {file.filename}, Content-Type: {file.content_type}")
        
        audio_data = await file.read()
        print(f"Audio data size: {len(audio_data)} bytes")
        
        print("Starting transcription with AssemblyAI...")
        transcript = transcriber.transcribe(audio_data)
        
        if transcript.status == aai.TranscriptStatus.error:
            print(f"Transcription failed: {transcript.error}")
            return {
                "error": f"Transcription failed: {transcript.error}",
                "status": "error"
            }
        
        transcribed_text = transcript.text
        print(f"Transcription completed: {transcribed_text}")
        
        if not transcribed_text or transcribed_text.strip() == "":
            return {
                "error": "No speech detected in the audio",
                "status": "error"
            }
        
        print("Generating speech with Murf API...")
        murf_url = "https://api.murf.ai/v1/speech/generate-with-key"
        
        murf_headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "api-key": os.getenv("MURF_API_KEY")
        }
        
        murf_payload = {
            "text": transcribed_text,
            "voiceId": "en-US-marcus",
            "format": "MP3"
        }
        
        murf_response = requests.post(murf_url, headers=murf_headers, json=murf_payload)
        
        if murf_response.status_code != 200:
            print(f"Murf API failed: {murf_response.status_code} - {murf_response.text}")
            return {
                "error": f"Speech generation failed: {murf_response.text}",
                "status": "error"
            }
        
        murf_result = murf_response.json()
        audio_url = murf_result.get("audioFile")
        
        if not audio_url:
            print("No audio URL in Murf response")
            return {
                "error": "No audio URL received from Murf API",
                "status": "error"
            }
        
        print(f"Echo bot completed successfully. Audio URL: {audio_url}")
        
        response_data = {
            "status": "success",
            "original_filename": file.filename,
            "transcribed_text": transcribed_text,
            "audio_url": audio_url,
            "voice_id": "en-US-marcus",
            "audio_duration": transcript.audio_duration,
            "words_count": len(transcribed_text.split()) if transcribed_text else 0
        }
        
        return response_data
        
    except Exception as e:
        print(f"Error in echo bot: {str(e)}")
        return {
            "error": f"Echo bot error: {str(e)}",
            "status": "error"
        }

@app.post("/llm/query")
async def llm_query(file: UploadFile = File(...)):
    """Voice LLM query with comprehensive error handling and fallbacks"""
    try:
        logger.info(f"Received audio for LLM query: {file.filename}, Content-Type: {file.content_type}")
        
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        audio_data = await file.read()
        logger.info(f"Audio data size: {len(audio_data)} bytes")
        
        if len(audio_data) == 0:
            raise HTTPException(status_code=400, detail="Empty audio file")
        
        logger.info("Step 1: Transcribing audio with AssemblyAI...")
        transcription_result = await safe_transcribe(audio_data)
        
        if not transcription_result["success"]:
            fallback_message = "I'm having trouble connecting right now"
            fallback_audio = await generate_fallback_audio_url(fallback_message)
            return {
                "status": "error",
                "error": transcription_result["error"],
                "fallback_message": fallback_message,
                "audioFile": fallback_audio,
                "original_filename": file.filename,
                "timestamp": datetime.now().isoformat()
            }
        
        user_query = transcription_result["text"]
        logger.info(f"User query: {user_query}")
        
        if not user_query or user_query.strip() == "":
            fallback_message = "I'm having trouble connecting right now"
            fallback_audio = await generate_fallback_audio_url(fallback_message)
            return {
                "status": "error",
                "error": "No speech detected in the audio",
                "fallback_message": fallback_message,
                "audioFile": fallback_audio,
                "original_filename": file.filename,
                "timestamp": datetime.now().isoformat()
            }
        
        logger.info("Step 2: Generating LLM response with Gemini AI...")
        llm_result = await safe_llm_generate(user_query)
        
        if not llm_result["success"]:
            ai_response_text = llm_result["fallback_response"]
            llm_success = False
        else:
            ai_response_text = llm_result["text"]
            llm_success = True
        
        logger.info(f"AI response: {ai_response_text[:100]}...")
        
        logger.info("Step 3: Converting AI response to speech with Murf...")
        tts_result = await safe_tts_generate(ai_response_text)
        
        if tts_result["success"]:
            audio_url = tts_result["audio_url"]
            tts_success = True
        else:
            logger.info("TTS failed, generating fallback audio with error message")
            fallback_message = "I'm having trouble connecting right now"
            audio_url = await generate_fallback_audio_url(fallback_message)
            tts_success = False
        
        if transcription_result["success"] and llm_success and tts_success:
            status = "success"
        elif transcription_result["success"]:
            status = "partial_success"
        else:
            status = "fallback"
        
        logger.info(f"Voice LLM query completed with status: {status}")
        
        response_data = {
            "status": status,
            "original_filename": file.filename,
            "user_query": user_query,
            "llm_response": ai_response_text,
            "audioFile": audio_url,
            "voice_id": "en-US-marcus",
            "model": "gemini-1.5-flash",
            "audio_duration": transcription_result.get("duration"),
            "timestamp": datetime.now().isoformat(),
            "service_status": {
                "transcription": transcription_result["success"],
                "llm": llm_success,
                "tts": tts_success
            }
        }
        
        if not llm_success:
            response_data["llm_error"] = llm_result["error"]
            response_data["fallback_message"] = FALLBACK_RESPONSES["llm_error"]
        
        if not tts_success:
            response_data["tts_error"] = tts_result["error"]
            response_data["tts_fallback_message"] = FALLBACK_RESPONSES["tts_error"]
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in voice LLM query: {str(e)}")
        return {
            "status": "error",
            "error": f"Voice LLM query error: {str(e)}",
            "fallback_message": FALLBACK_RESPONSES["general_error"],
            "original_filename": getattr(file, 'filename', 'unknown'),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/agent/chat/{session_id}")
async def conversational_agent(session_id: str, file: UploadFile = File(...)):
    try:
        print(f"Received audio for conversation session: {session_id}, File: {file.filename}")
        
        if session_id not in chat_sessions:
            chat_sessions[session_id] = {
                "messages": [],
                "created_at": datetime.now().isoformat(),
                "last_activity": datetime.now().isoformat()
            }
            print(f"Created new chat session: {session_id}")
        
        audio_data = await file.read()
        print(f"Audio data size: {len(audio_data)} bytes")
        
        print("Step 1: Transcribing audio with AssemblyAI...")
        transcript = transcriber.transcribe(audio_data)
        
        if transcript.status == aai.TranscriptStatus.error:
            print(f"Transcription failed: {transcript.error}")
            return {
                "error": f"Transcription failed: {transcript.error}",
                "status": "error"
            }
        
        user_message = transcript.text
        print(f"User message: {user_message}")
        
        if not user_message or user_message.strip() == "":
            return {
                "error": "No speech detected in the audio",
                "status": "error"
            }
        
        chat_sessions[session_id]["messages"].append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat()
        })
        chat_sessions[session_id]["last_activity"] = datetime.now().isoformat()
        
        conversation_context = "You are a helpful and friendly AI assistant having a natural conversation. Keep your responses conversational and engaging.\n\nConversation history:\n"
        
        for msg in chat_sessions[session_id]["messages"]:
            if msg["role"] == "user":
                conversation_context += f"User: {msg['content']}\n"
            else:
                conversation_context += f"Assistant: {msg['content']}\n"
        
        conversation_context += "\nPlease respond to the user's latest message naturally, considering the conversation history."
        
        print(f"Conversation context length: {len(conversation_context)} characters")
        
        print("Step 4: Generating contextual AI response with Gemini...")
        llm_response = gemini_model.generate_content(conversation_context)
        
        if not llm_response.text:
            return {
                "error": "No response generated from Gemini AI",
                "status": "error"
            }
        
        ai_response_text = llm_response.text.strip()
        print(f"AI response: {ai_response_text[:100]}...")
        
        chat_sessions[session_id]["messages"].append({
            "role": "assistant",
            "content": ai_response_text,
            "timestamp": datetime.now().isoformat()
        })
        
        print("Step 6: Converting AI response to speech with Murf...")
        murf_url = "https://api.murf.ai/v1/speech/generate-with-key"
        
        murf_headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "api-key": os.getenv("MURF_API_KEY")
        }
        
        murf_payload = {
            "text": ai_response_text,
            "voiceId": "en-US-marcus",
            "format": "MP3"
        }
        
        murf_response = requests.post(murf_url, headers=murf_headers, json=murf_payload)
        
        if murf_response.status_code != 200:
            print(f"Murf API failed: {murf_response.status_code} - {murf_response.text}")
            return {
                "error": f"Speech generation failed: {murf_response.text}",
                "status": "error"
            }
        
        murf_result = murf_response.json()
        audio_url = murf_result.get("audioFile")
        
        if not audio_url:
            print("No audio URL in Murf response")
            return {
                "error": "No audio URL received from Murf API",
                "status": "error"
            }
        
        print(f"Conversational agent completed successfully. Session: {session_id}")
        
        response_data = {
            "status": "success",
            "session_id": session_id,
            "original_filename": file.filename,
            "user_message": user_message,
            "ai_response": ai_response_text,
            "audioFile": audio_url,
            "voice_id": "en-US-marcus",
            "model": "gemini-1.5-flash",
            "audio_duration": transcript.audio_duration,
            "message_count": len(chat_sessions[session_id]["messages"]),
            "timestamp": datetime.now().isoformat()
        }
        
        return response_data
        
    except Exception as e:
        print(f"Error in conversational agent: {str(e)}")
        return {
            "error": f"Conversational agent error: {str(e)}",
            "status": "error"
        }

@app.get("/agent/chat/{session_id}/history")
async def get_chat_history(session_id: str):
    """Get chat history for a session"""
    try:
        if session_id not in chat_sessions:
            return {
                "session_id": session_id,
                "messages": [],
                "message_count": 0,
                "status": "new_session"
            }
        
        session = chat_sessions[session_id]
        return {
            "session_id": session_id,
            "messages": session["messages"],
            "message_count": len(session["messages"]),
            "created_at": session["created_at"],
            "last_activity": session["last_activity"],
            "status": "active"
        }
        
    except Exception as e:
        print(f"Error getting chat history: {str(e)}")
        return {
            "error": f"Chat history error: {str(e)}",
            "status": "error"
        }

@app.post("/conversation/query")
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
        
        logger.info("Step 1: Transcribing audio...")
        transcription_result = await safe_transcribe(audio_data)
        
        if not transcription_result["success"]:
            fallback_message = FALLBACK_RESPONSES["stt_error"]
            fallback_audio = await generate_fallback_audio_url(fallback_message)
            return {
                "status": "error",
                "error": transcription_result["error"],
                "ai_response": fallback_message,
                "audioFile": fallback_audio,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
        
        user_query = transcription_result["text"]
        logger.info(f"User query: {user_query}")
        
        if not user_query or user_query.strip() == "":
            fallback_message = "I didn't catch that. Could you please repeat?"
            fallback_audio = await generate_fallback_audio_url(fallback_message)
            return {
                "status": "error",
                "error": "No speech detected",
                "ai_response": fallback_message,
                "audioFile": fallback_audio,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
        
        if not session_id:
            session_id = f"session_{int(datetime.now().timestamp())}"
        
        if session_id not in chat_sessions:
            chat_sessions[session_id] = {
                "messages": [],
                "created_at": datetime.now().isoformat(),
                "last_activity": datetime.now().isoformat()
            }
        
        session = chat_sessions[session_id]
        session["last_activity"] = datetime.now().isoformat()
        
        session["messages"].append({
            "role": "user",
            "content": user_query,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info("Step 2: Generating AI response with conversation context...")
        
        context_messages = []
        for msg in session["messages"][-10:]:
            context_messages.append(f"{msg['role'].title()}: {msg['content']}")
        
        conversation_context = "\n".join(context_messages)
        
        prompt = f"""You are a helpful AI assistant having a natural conversation. 
        
Previous conversation:
{conversation_context}

Please respond naturally and conversationally to the user's latest message. Keep your response concise but helpful."""
        
        llm_result = await safe_llm_generate(prompt)
        
        if not llm_result["success"]:
            ai_response_text = llm_result["fallback_response"]
            llm_success = False
        else:
            ai_response_text = llm_result["text"]
            llm_success = True
        
        session["messages"].append({
            "role": "assistant",
            "content": ai_response_text,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"AI response: {ai_response_text[:100]}...")
        
        logger.info("Step 3: Converting AI response to speech...")
        tts_result = await safe_tts_generate(ai_response_text)
        
        if tts_result["success"]:
            audio_url = tts_result["audio_url"]
            tts_success = True
        else:
            logger.info("TTS failed, generating fallback audio")
            audio_url = await generate_fallback_audio_url(ai_response_text)
            tts_success = False
        
        if transcription_result["success"] and llm_success and tts_success:
            status = "success"
        elif transcription_result["success"]:
            status = "partial_success"
        else:
            status = "fallback"
        
        logger.info(f"Conversation query completed with status: {status}")
        
        response_data = {
            "status": status,
            "session_id": session_id,
            "user_query": user_query,
            "ai_response": ai_response_text,
            "audioFile": audio_url,
            "voice_id": "en-US-marcus",
            "model": "gemini-1.5-flash",
            "message_count": len(session["messages"]),
            "audio_duration": transcription_result.get("duration"),
            "timestamp": datetime.now().isoformat(),
            "service_status": {
                "transcription": transcription_result["success"],
                "llm": llm_success,
                "tts": tts_success
            }
        }
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in conversation query: {e}")
        fallback_message = FALLBACK_RESPONSES["general_error"]
        fallback_audio = await generate_fallback_audio_url(fallback_message)
        return {
            "status": "error",
            "error": str(e),
            "ai_response": fallback_message,
            "audioFile": fallback_audio,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }

