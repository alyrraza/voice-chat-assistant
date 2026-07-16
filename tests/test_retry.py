import pytest

from services.retry import with_retry


def test_with_retry_retries_then_succeeds():
    calls = {"count": 0}

    @with_retry(max_attempts=3, base_delay=0)
    def flaky():
        calls["count"] += 1
        if calls["count"] < 2:
            raise ValueError("boom")
        return "ok"

    assert flaky() == "ok"
    assert calls["count"] == 2


def test_with_retry_raises_after_max_attempts():
    @with_retry(max_attempts=2, base_delay=0)
    def always_fails():
        raise ValueError("boom")

    with pytest.raises(ValueError):
        always_fails()
