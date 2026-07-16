"""POST raw audio bytes -> {"transcript": "..."} — Vercel Python serverless function.

The frontend POSTs the recorded Blob directly as the request body (with its
mimetype as Content-Type), not multipart form data — simpler on both ends.
"""
import json
from http.server import BaseHTTPRequestHandler

from services.stt_batch import transcribe


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        audio_bytes = self.rfile.read(length)
        content_type = self.headers.get("Content-Type", "audio/webm")

        try:
            transcript = transcribe(audio_bytes, content_type)
            self._send_json(200, {"transcript": transcript})
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def _send_json(self, status: int, payload: dict):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
