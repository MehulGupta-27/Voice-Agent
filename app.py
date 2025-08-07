from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import requests
from pathlib import Path

load_dotenv()

app = FastAPI()

# Create uploads directory if it doesn't exist
uploads_dir = Path("uploads")
try:
    uploads_dir.mkdir(exist_ok=True)
    print(f"✅ Uploads directory ready: {uploads_dir.absolute()}")
except Exception as e:
    print(f"❌ Error creating uploads directory: {e}")
    uploads_dir = Path(".")

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
    # print("Murf Response:", response.status_code, response.text)


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

