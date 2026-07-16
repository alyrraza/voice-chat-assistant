"""Text-to-speech via Deepgram's cloud TTS API (no local voice model)."""
import base64

import requests

from . import config


def synthesize_html(text: str) -> str | None:
    """Converts text to speech and returns an autoplaying HTML <audio> snippet.

    Returns None if the request fails; caller decides how to surface that.
    """
    headers = {
        "Authorization": f"Token {config.DEEPGRAM_API_KEY}",
        "Content-Type": "application/json",
    }
    response = requests.post(
        config.DEEPGRAM_TTS_URL, headers=headers, json={"text": text}, timeout=15
    )
    if response.status_code != 200:
        return None

    audio_base64 = base64.b64encode(response.content).decode("utf-8")
    return f"""
        <audio autoplay>
            <source src="data:audio/wav;base64,{audio_base64}" type="audio/wav">
        </audio>
    """
