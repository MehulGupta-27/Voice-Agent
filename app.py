from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import requests
from pathlib import Path
import assemblyai as aai
import google.generativeai as genai
from datetime import datetime


load_dotenv()

app = FastAPI()

uploads_dir = Path("uploads")
try:
    uploads_dir.mkdir(exist_ok=True)
    print(f"✅ Uploads directory ready: {uploads_dir.absolute()}")
except Exception as e:
    print(f"❌ Error creating uploads directory: {e}")
    uploads_dir = Path(".")

aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")
transcriber = aai.Transcriber()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
gemini_model = genai.GenerativeModel('gemini-1.5-flash')

chat_sessions = {}
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TTSRequest(BaseModel):
    text: str
    voiceId: str
    format: str = "MP3"

class LLMRequest(BaseModel):
    text: str

@app.get("/")
def working():
    return {
        "message": "API working good"
    }

@app.post("/generate-audio")
async def generate_audio(req: TTSRequest):
    url = "https://api.murf.ai/v1/speech/generate-with-key"

    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "api-key": os.getenv("MURF_API_KEY")
    }

    payload = {
            "text": req.text,
            "voiceId": req.voiceId,
            "format": req.format

    }

    response = requests.post(url, headers=headers, json=payload)


    return {
        "audio": response.json()
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
    try:
        print(f"Received audio for LLM query: {file.filename}, Content-Type: {file.content_type}")
        
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
        
        user_query = transcript.text
        print(f"User query: {user_query}")
        
        if not user_query or user_query.strip() == "":
            return {
                "error": "No speech detected in the audio",
                "status": "error"
            }
        
        print("Step 2: Generating LLM response with Gemini AI...")
        llm_response = gemini_model.generate_content(user_query)
        
        if not llm_response.text:
            return {
                "error": "No response generated from Gemini AI",
                "status": "error"
            }
        
        ai_response_text = llm_response.text.strip()
        print(f"LLM response: {ai_response_text[:100]}...")
        
        print("Step 3: Converting LLM response to speech with Murf...")
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
        
        print(f"Voice LLM query completed successfully. Audio URL: {audio_url}")
        
        response_data = {
            "status": "success",
            "original_filename": file.filename,
            "user_query": user_query,
            "llm_response": ai_response_text,
            "audioFile": audio_url,
            "voice_id": "en-US-marcus",
            "model": "gemini-1.5-flash",
            "audio_duration": transcript.audio_duration,
            "timestamp": datetime.now().isoformat()
        }
        
        return response_data
        
    except Exception as e:
        print(f"Error in voice LLM query: {str(e)}")
        return {
            "error": f"Voice LLM query error: {str(e)}",
            "status": "error"
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

