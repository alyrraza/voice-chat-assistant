"""Single Vercel Python entrypoint, internally routed by ?action=.

Vercel's Python runtime expects exactly one declared entrypoint per project
(see pyproject.toml), not one file per route — so chat/transcribe/speak all
live here and dispatch based on the `action` query param the frontend sends
(e.g. POST /api/index?action=chat).
"""
import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from services.llm import get_reply
from services.stt_batch import transcribe
from services.tts import synthesize_audio_bytes


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
