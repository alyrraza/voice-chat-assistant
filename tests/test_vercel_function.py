import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "frontend" / "api"))
import backend as vercel_api  # noqa: E402


def test_get_reply_returns_content():
    fake_response = MagicMock()
    fake_response.choices = [MagicMock(message=MagicMock(content="Hello there"))]
    vercel_api._groq_client = None

    with patch("backend._client") as mock_client:
        mock_client.return_value.chat.completions.create.return_value = fake_response
        reply = vercel_api.get_reply([{"role": "user", "content": "hi"}])

    assert reply == "Hello there"


def test_transcribe_returns_transcript():
    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None
    fake_response.json.return_value = {
        "results": {"channels": [{"alternatives": [{"transcript": "hi"}]}]}
    }

    with patch("backend.requests.post", return_value=fake_response):
        assert vercel_api.transcribe(b"audio", "audio/webm") == "hi"


def test_synthesize_audio_bytes_returns_bytes():
    fake_response = MagicMock(content=b"fake-audio")
    fake_response.raise_for_status.return_value = None

    with patch("backend.requests.post", return_value=fake_response):
        assert vercel_api.synthesize_audio_bytes("hi") == b"fake-audio"
