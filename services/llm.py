"""Chat completion via Groq's cloud API (replaces the original local Ollama call)."""
import logging

from groq import Groq

from . import config
from .retry import with_retry

logger = logging.getLogger(__name__)

_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=config.GROQ_API_KEY)
    return _client


@with_retry(max_attempts=3, base_delay=1.0)
def get_reply(chat_history: list[dict]) -> str:
    """Sends the full conversation so far and returns the assistant's reply.

    Unlike the original ollama.invoke(text) call (which only ever saw the
    latest utterance), this sends the whole chat_history so the assistant
    actually has conversational memory.
    """
    logger.info("Sending %d-message conversation to Groq (%s)", len(chat_history), config.GROQ_MODEL)
    response = _get_client().chat.completions.create(
        model=config.GROQ_MODEL,
        messages=chat_history,
    )
    reply = response.choices[0].message.content
    logger.info("Received Groq reply (%d chars)", len(reply))
    return reply
