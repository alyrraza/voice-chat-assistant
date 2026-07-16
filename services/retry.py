"""Retry-with-exponential-backoff for calls to third-party APIs.

External AI services (LLM/STT/TTS providers) fail transiently — rate limits,
timeouts, brief outages. Retrying with backoff instead of failing on the
first error is standard practice for any app that leans on external APIs.
"""
import functools
import logging
import time

logger = logging.getLogger(__name__)


def with_retry(max_attempts: int = 3, base_delay: float = 1.0):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    if attempt >= max_attempts:
                        logger.error(
                            "%s failed after %d attempts: %s", func.__name__, attempt, e
                        )
                        raise
                    delay = base_delay * (2 ** (attempt - 1))
                    logger.warning(
                        "%s failed (attempt %d/%d): %s — retrying in %.1fs",
                        func.__name__, attempt, max_attempts, e, delay,
                    )
                    time.sleep(delay)
        return wrapper
    return decorator
