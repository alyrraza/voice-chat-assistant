"""Chat completion via Groq's cloud API (replaces the original local Ollama call)."""
from groq import Groq

from . import config

_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=config.GROQ_API_KEY)
    return _client


def get_reply(chat_history: list[dict]) -> str:
    """Sends the full conversation so far and returns the assistant's reply.

    Unlike the original ollama.invoke(text) call (which only ever saw the
    latest utterance), this sends the whole chat_history so the assistant
    actually has conversational memory.
    """
    response = _get_client().chat.completions.create(
        model=config.GROQ_MODEL,
        messages=chat_history,
    )
    return response.choices[0].message.content
