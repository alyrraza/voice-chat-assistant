from unittest.mock import MagicMock, patch

from services import llm


def test_get_reply_returns_content():
    fake_response = MagicMock()
    fake_response.choices = [MagicMock(message=MagicMock(content="Hello there"))]

    with patch("services.llm._get_client") as mock_get_client:
        mock_get_client.return_value.chat.completions.create.return_value = fake_response
        reply = llm.get_reply([{"role": "user", "content": "hi"}])

    assert reply == "Hello there"


def test_get_reply_sends_full_history():
    fake_response = MagicMock()
    fake_response.choices = [MagicMock(message=MagicMock(content="ok"))]
    history = [
        {"role": "system", "content": "be nice"},
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
        {"role": "user", "content": "how are you"},
    ]

    with patch("services.llm._get_client") as mock_get_client:
        create = mock_get_client.return_value.chat.completions.create
        create.return_value = fake_response
        llm.get_reply(history)

    assert create.call_args.kwargs["messages"] == history
