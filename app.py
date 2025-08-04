from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import requests

load_dotenv()

app = FastAPI()

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
