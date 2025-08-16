import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Directories
BASE_DIR = Path(__file__).parent
UPLOADS_DIR = BASE_DIR / "uploads"
FALLBACK_AUDIO_DIR = BASE_DIR / "fallback_audio"

# API Keys
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MURF_API_KEY = os.getenv("MURF_API_KEY")

# Service Settings
DEFAULT_VOICE_ID = "en-US-marcus"
DEFAULT_TTS_FORMAT = "MP3"
DEFAULT_LLM_MODEL = "gemini-1.5-flash"

# Retry Settings
MAX_RETRIES_STT = 3
MAX_RETRIES_LLM = 3
MAX_RETRIES_TTS = 3

# Timeout Settings
TTS_TIMEOUT = 30
FALLBACK_TIMEOUT = 30

# Conversation Settings
MAX_CONTEXT_MESSAGES = 10

# Logging Configuration
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        'default': {
            'level': 'INFO',
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        '': {
            'handlers': ['default'],
            'level': 'INFO',
            'propagate': False
        }
    }
}