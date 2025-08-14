# Voice AI Assistant

A simple voice-powered AI assistant that lets you have natural conversations with AI. Speak to it, and it responds back with voice.

## Features

- Voice recognition (speech-to-text)
- AI conversations with context memory
- Text-to-speech responses
- Continuous conversation mode
- Clean, minimal interface

## Technologies Used: 

- **Frontend**: HTML, CSS, JavaScript
- **Backend**: Python, FastAPI
- **AI Services**: AssemblyAI, Google Gemini, Murf AI

## Setup

### 1. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 2. Get API Keys
You need API keys from these services:
- [AssemblyAI](https://www.assemblyai.com/) - for speech recognition
- [Google AI Studio](https://makersuite.google.com/) - for AI conversations
- [Murf AI](https://murf.ai/) - for text-to-speech

### 3. Create .env file
Create a `.env` file in the project root:
```
ASSEMBLYAI_API_KEY=your_assemblyai_key
GEMINI_API_KEY=your_gemini_key
MURF_API_KEY=your_murf_key
```

### 4. Run the application
```bash
# Start the server
python -m uvicorn app:app --reload --port 8000

# Open index.html in your browser
```

## Usage

1. Open the web interface
2. Allow microphone permissions
3. Click the microphone button and speak
4. The AI will respond with voice
5. The conversation continues automatically

## Project Structure

```
├── app.py          # FastAPI backend server
├── index.html      # Web interface
├── main.js         # Frontend JavaScript
├── style.css       # Styling
├── requirements.txt # Python dependencies
└── .env            # API keys (create this)
```

## API Endpoints

- `GET /health` - Check server status
- `POST /conversation/query` - Send voice message and get AI response
- `POST /generate-audio` - Convert text to speech

## Troubleshooting

- **Microphone not working**: Check browser permissions
- **API errors**: Verify your API keys in .env file
- **Server won't start**: Make sure port 8000 is available

## License

MIT License