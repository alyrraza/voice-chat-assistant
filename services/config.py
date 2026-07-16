"""Loads configuration and API keys from the environment (.env in dev)."""
import os

from dotenv import load_dotenv

load_dotenv()

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

DEEPGRAM_STT_URL = (
    "wss://api.deepgram.com/v1/listen"
    "?encoding=linear16&sample_rate=16000&channels=1&punctuate=true&model=general"
)
DEEPGRAM_TTS_URL = "https://api.deepgram.com/v1/speak?model=aura-asteria-en"

SAMPLE_RATE = 16000
CHANNELS = 1


def missing_keys() -> list[str]:
    """Returns a list of required env vars that are not set."""
    missing = []
    if not DEEPGRAM_API_KEY:
        missing.append("DEEPGRAM_API_KEY")
    if not GROQ_API_KEY:
        missing.append("GROQ_API_KEY")
    return missing
