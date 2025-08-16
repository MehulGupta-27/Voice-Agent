# Voice AI Assistant

A production-ready voice-powered AI assistant that enables natural conversations with AI. Speak to it, and it responds back with voice using state-of-the-art AI services.

## Features

- **Voice Recognition**: High-quality speech-to-text using AssemblyAI
- **AI Conversations**: Contextual conversations with Google Gemini
- **Text-to-Speech**: Natural voice synthesis with Murf AI
- **Session Management**: Persistent conversation history
- **Fallback System**: Robust error handling with backup TTS
- **Continuous Mode**: Seamless conversation flow
- **Clean Architecture**: Modular, maintainable codebase

## Technologies Used

- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Backend**: Python 3.8+, FastAPI, Pydantic
- **AI Services**: 
  - AssemblyAI (Speech-to-Text)
  - Google Gemini 1.5 Flash (LLM)
  - Murf AI (Text-to-Speech)
- **Fallback**: gTTS for offline TTS support

## Project Structure

```
voice-ai-assistant/
├── app.py                 # FastAPI application
├── config.py             # Configuration settings
├── schemas.py            # Pydantic models
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables (create this)
├── .gitignore           # Git ignore rules
├── services/            # Service layer
│   ├── __init__.py
│   ├── stt_service.py   # Speech-to-Text service
│   ├── llm_service.py   # Language Model service
│   ├── tts_service.py   # Text-to-Speech service
│   ├── fallback_service.py  # Fallback audio service
│   └── session_manager.py   # Session management
├── uploads/             # Temporary audio files
├── fallback_audio/      # Cached fallback audio
├── index.html          # Web interface
├── main.js            # Frontend JavaScript
└── style.css          # Styling
```

## Setup Instructions

### 1. Clone and Install Dependencies

```bash
git clone <your-repo-url>
cd voice-ai-assistant
pip install -r requirements.txt
```

### 2. Get API Keys

You need API keys from these services:

- **[AssemblyAI](https://www.assemblyai.com/)** - for speech recognition
  - Sign up and get your API key from the dashboard
- **[Google AI Studio](https://makersuite.google.com/)** - for AI conversations  
  - Create a project and generate an API key for Gemini
- **[Murf AI](https://murf.ai/)** - for text-to-speech
  - Sign up for an account and get your API key

### 3. Create Environment File

Create a `.env` file in the project root:

```env
ASSEMBLYAI_API_KEY=your_assemblyai_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
MURF_API_KEY=your_murf_api_key_here
```

### 4. Run the Application

```bash
# Start the FastAPI server
python -m uvicorn app:app --reload --port 8000

# Or run directly
python app.py
```

Then open `index.html` in your browser or serve it locally:

```bash
# Optional: serve frontend with Python
python -m http.server 3000
# Then visit http://localhost:3000
```

## Usage

1. **Open the web interface** - Load `index.html` in your browser
2. **Allow microphone permissions** when prompted
3. **Start conversation** - Click the microphone button and speak
4. **Wait for response** - The AI will respond with voice
5. **Continue chatting** - The conversation continues automatically

## API Endpoints

### Core Endpoints
- `GET /` - API status and service health
- `GET /health` - Comprehensive health check
- `POST /conversation/query` - Main conversational endpoint

### Audio Processing
- `POST /upload-audio` - Upload audio files
- `POST /transcribe/file` - Transcribe audio to text
- `POST /generate-audio` - Convert text to speech
- `POST /tts/echo` - Echo bot (transcribe → speak back)

### Session Management  
- `POST /agent/chat/{session_id}` - Chat with session context
- `GET /agent/chat/{session_id}/history` - Get conversation history

### Fallback Audio
- `GET /generate-fallback-audio/{message}` - Generate fallback audio
- `GET /list-fallback-audio` - List all fallback audio files
- `GET /download-fallback-audio/{filename}` - Download fallback audio

## Configuration

Key settings can be modified in `config.py`:

```python
# Voice and model settings
DEFAULT_VOICE_ID = "en-US-marcus"  # Murf voice ID
DEFAULT_LLM_MODEL = "gemini-1.5-flash"  # Gemini model

# Retry and timeout settings
MAX_RETRIES_STT = 3
MAX_RETRIES_LLM = 3
MAX_RETRIES_TTS = 3
TTS_TIMEOUT = 30
```

## Architecture

### Services Layer
- **STTService**: Handles speech-to-text with AssemblyAI
- **LLMService**: Manages AI conversations with Gemini
- **TTSService**: Converts text to speech with Murf AI
- **FallbackService**: Provides backup audio generation
- **SessionManager**: Manages conversation sessions and context

### Error Handling
- Comprehensive retry logic with exponential backoff
- Graceful fallbacks for each service layer
- User-friendly error messages
- Offline TTS support with gTTS

### Performance Features
- Caching of fallback audio files
- Optimized conversation context management
- Efficient session storage
- Async/await for non-blocking operations

## Troubleshooting

### Common Issues

**Microphone not working**
- Check browser permissions for microphone access
- Ensure HTTPS or localhost for microphone API access

**API errors**
- Verify all API keys are correctly set in `.env` file
- Check API key permissions and quotas
- Review logs for specific error messages

**Server won't start**
- Ensure port 8000 is available
- Check Python version (3.8+ required)
- Verify all dependencies are installed

**Audio playback issues**
- Check browser audio permissions
- Try different browsers (Chrome recommended)
- Ensure network connectivity for audio URLs

###