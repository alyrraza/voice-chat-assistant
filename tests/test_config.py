from services import config


def test_missing_keys_reports_absent_vars(monkeypatch):
    monkeypatch.setattr(config, "DEEPGRAM_API_KEY", "")
    monkeypatch.setattr(config, "GROQ_API_KEY", "")
    assert config.missing_keys() == ["DEEPGRAM_API_KEY", "GROQ_API_KEY"]


def test_missing_keys_empty_when_both_set(monkeypatch):
    monkeypatch.setattr(config, "DEEPGRAM_API_KEY", "x")
    monkeypatch.setattr(config, "GROQ_API_KEY", "y")
    assert config.missing_keys() == []
