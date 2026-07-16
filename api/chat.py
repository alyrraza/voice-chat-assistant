"""POST {"messages": [...]} -> {"reply": "..."} — Vercel Python serverless function."""
import json
from http.server import BaseHTTPRequestHandler

from services.llm import get_reply


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")

        try:
            reply = get_reply(body["messages"])
            self._send_json(200, {"reply": reply})
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def _send_json(self, status: int, payload: dict):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
