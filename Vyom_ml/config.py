from pydantic_settings import BaseSettings
from typing import Dict
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseSettings):
    # API Keys
    SARVAM_API_KEY: str = os.getenv("SARVAM_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    
    # API Endpoints
    STT_URL: str = "https://api.sarvam.ai/speech-to-text-translate"
    TTS_URL: str = "https://api.sarvam.ai/text-to-speech"
    TRANS_URL: str = "https://api.sarvam.ai/translate"
    
    # Audio Settings
    AUDIO_FORMAT: int = 16  # paInt16
    CHANNELS: int = 1
    RATE: int = 16000
    FRAME_DURATION_MS: int = 20
    SILENCE_LIMIT: int = RATE // (RATE * (FRAME_DURATION_MS / 1000))
    
    # Supported Languages
    SUPPORTED_LANGUAGES: Dict[str, str] = {
        "en": "en-IN",
        "hi": "hi-IN",
        "mr": "mr-IN",
        "kn": "kn-IN"
    }
    
    # File Paths
    TEMP_AUDIO_PATH: str = "temp_audio.wav"
    
    class Config:
        env_file = ".env"

settings = Settings() 