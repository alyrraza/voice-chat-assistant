"""Prerecorded (batch) speech-to-text via Deepgram — for serverless use.

Unlike services/stt.py (which streams live mic audio over a websocket),
this takes a single already-recorded audio blob — exactly what a browser's
MediaRecorder hands over — and posts it to Deepgram's prerecorded REST
endpoint. No sounddevice/mic access needed, so it's safe to run inside a
Vercel serverless function that has no physical microphone.
"""
import logging

import requests

from . import config
from .retry import with_retry

logger = logging.getLogger(__name__)

DEEPGRAM_PRERECORDED_URL = "https://api.deepgram.com/v1/listen?punctuate=true&model=general"


@with_retry(max_attempts=3, base_delay=1.0)
def transcribe(audio_bytes: bytes, content_type: str) -> str:
    headers = {
        "Authorization": f"Token {config.DEEPGRAM_API_KEY}",
        "Content-Type": content_type,
    }
    logger.info("Transcribing %d bytes of %s audio", len(audio_bytes), content_type)
    response = requests.post(
        DEEPGRAM_PRERECORDED_URL, headers=headers, data=audio_bytes, timeout=30
    )
    response.raise_for_status()

    result = response.json()
    transcript = result["results"]["channels"][0]["alternatives"][0]["transcript"]
    logger.info("Transcript: %r", transcript)
    return transcript
