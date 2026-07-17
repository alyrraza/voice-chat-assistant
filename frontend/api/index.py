"""Self-contained Vercel serverless function: chat (Groq), transcribe + speak (Deepgram).

Deliberately self-contained (no imports from the repo-root services/ package)
so this keeps working regardless of Vercel's Root Directory setting — it only
depends on pip packages listed in frontend/api/requirements.txt.
"""
import json
import os
import time
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

import requests
from groq import Groq

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY", "")
DEEPGRAM_STT_URL = "https://api.deepgram.com/v1/listen?punctuate=true&model=general"
DEEPGRAM_TTS_URL = "https://api.deepgram.com/v1/speak?model=aura-asteria-en"

_groq_client = None


def _client() -> Groq:
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=GROQ_API_KEY)
    return _groq_client


def _with_retry(fn, *args, max_attempts=3, base_delay=1.0, **kwargs):
    for attempt in range(1, max_attempts + 1):
        try:
            return fn(*args, **kwargs)
        except Exception:
            if attempt == max_attempts:
                raise
            time.sleep(base_delay * (2 ** (attempt - 1)))


def get_reply(messages: list[dict]) -> str:
    def _call():
        response = _client().chat.completions.create(model=GROQ_MODEL, messages=messages)
        return response.choices[0].message.content

    return _with_retry(_call)


def transcribe(audio_bytes: bytes, content_type: str) -> str:
    def _call():
        headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}", "Content-Type": content_type}
        r = requests.post(DEEPGRAM_STT_URL, headers=headers, data=audio_bytes, timeout=30)
        r.raise_for_status()
        return r.json()["results"]["channels"][0]["alternatives"][0]["transcript"]

    return _with_retry(_call)


def synthesize_audio_bytes(text: str) -> bytes:
    def _call():
        headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}", "Content-Type": "application/json"}
        r = requests.post(DEEPGRAM_TTS_URL, headers=headers, json={"text": text}, timeout=15)
        r.raise_for_status()
        return r.content

    return _with_retry(_call)


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        query = parse_qs(urlparse(self.path).query)
        action = query.get("action", [""])[0]

        if action == "chat":
            self._handle_chat()
        elif action == "transcribe":
            self._handle_transcribe()
        elif action == "speak":
            self._handle_speak()
        else:
            self._send_json(404, {"error": f"Unknown action: {action!r}"})

    def _handle_chat(self):
        body = self._read_json()
        try:
            reply = get_reply(body["messages"])
            self._send_json(200, {"reply": reply})
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def _handle_transcribe(self):
        length = int(self.headers.get("Content-Length", 0))
        audio_bytes = self.rfile.read(length)
        content_type = self.headers.get("Content-Type", "audio/webm")
        try:
            text = transcribe(audio_bytes, content_type)
            self._send_json(200, {"transcript": text})
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def _handle_speak(self):
        body = self._read_json()
        try:
            audio_bytes = synthesize_audio_bytes(body["text"])
            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Content-Length", str(len(audio_bytes)))
            self.end_headers()
            self.wfile.write(audio_bytes)
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length) or b"{}")

    def _send_json(self, status: int, payload: dict):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
