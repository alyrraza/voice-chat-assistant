from unittest.mock import MagicMock, patch

from services import stt_batch


def test_transcribe_returns_transcript_text():
    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None
    fake_response.json.return_value = {
        "results": {"channels": [{"alternatives": [{"transcript": "hello world"}]}]}
    }

    with patch("services.stt_batch.requests.post", return_value=fake_response):
        transcript = stt_batch.transcribe(b"fake-audio-bytes", "audio/webm")

    assert transcript == "hello world"
