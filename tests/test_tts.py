from unittest.mock import MagicMock, patch

from services import tts


def test_synthesize_html_returns_audio_tag():
    fake_response = MagicMock(content=b"fake-audio-bytes")
    fake_response.raise_for_status.return_value = None

    with patch("services.tts.requests.post", return_value=fake_response):
        html = tts.synthesize_html("hello")

    assert "<audio autoplay>" in html
    assert "data:audio/wav;base64," in html
