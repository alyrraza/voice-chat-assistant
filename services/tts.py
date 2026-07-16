"""Text-to-speech via Deepgram's cloud TTS API (no local voice model)."""
import base64
import logging

import requests

from . import config
from .retry import with_retry

logger = logging.getLogger(__name__)


@with_retry(max_attempts=3, base_delay=1.0)
def synthesize_html(text: str) -> str:
    """Converts text to speech and returns an autoplaying HTML <audio> snippet.

    Raises requests.HTTPError if Deepgram returns a non-2xx response — the
    retry decorator will retry transient failures before giving up.
    """
    headers = {
        "Authorization": f"Token {config.DEEPGRAM_API_KEY}",
        "Content-Type": "application/json",
    }
    logger.info("Requesting TTS for %d chars of text", len(text))
    response = requests.post(
        config.DEEPGRAM_TTS_URL, headers=headers, json={"text": text}, timeout=15
    )
    response.raise_for_status()

    audio_base64 = base64.b64encode(response.content).decode("utf-8")
    return f"""
        <audio autoplay>
            <source src="data:audio/wav;base64,{audio_base64}" type="audio/wav">
        </audio>
    """
