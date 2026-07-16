# 🎙️ Voice Chat Assistant

A real-time voice assistant in the browser: speak into your mic, get a live
transcript, a conversational LLM reply, and a spoken response back — all
through a Streamlit app, no local models or GPU required.

**Speech-to-text → LLM → Text-to-speech, entirely via cloud APIs.**

## Features

- 🎤 Live voice recording with one-click Start/Stop
- ⌨️ Text input fallback — type instead of speak, useful for demos
- 💬 Full conversational memory (the assistant sees the whole chat history, not just your last message)
- 🔊 Spoken replies with an autoplay/replay control
- ⚙️ Sidebar shows whether your API keys are configured
- 🛡️ Retry-with-backoff on external API calls, structured logging, and a unit test suite

## Architecture

```
🎤 Mic audio  ──(sounddevice)──▶  Deepgram STT (websocket, streaming)
                                          │
                                          ▼
                                   Transcript text
                                          │
                                          ▼
                              Groq LLM (chat completion,
                              full conversation history)
                                          │
                                          ▼
                                    Reply text
                                          │
                                          ▼
                              Deepgram TTS ──▶ 🔊 Spoken reply
```

All three integrations are thin, isolated modules under `services/`:

| File | Responsibility |
|---|---|
| `services/config.py` | Loads API keys/settings from `.env` |
| `services/stt.py` | Mic capture + streaming speech-to-text |
| `services/llm.py` | Chat completion via Groq |
| `services/tts.py` | Text-to-speech via Deepgram |
| `services/retry.py` | Retry-with-backoff decorator for flaky external calls |
| `services/logging_config.py` | One-line structured logging setup |
| `app.py` | Streamlit UI that wires it all together |

## Setup

1. **Clone the repo**
   ```bash
   git clone https://github.com/alyrraza/voice-chat-assistant.git
   cd voice-chat-assistant
   ```

2. **Create a virtual environment** (keeps dependencies out of your global Python)
   ```bash
   python -m venv .venv
   .venv\Scripts\activate      # Windows
   source .venv/bin/activate   # macOS/Linux
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Add your API keys** — copy `.env.example` to `.env` and fill in:
   - `DEEPGRAM_API_KEY` — free at [console.deepgram.com](https://console.deepgram.com)
   - `GROQ_API_KEY` — free at [console.groq.com/keys](https://console.groq.com/keys)

5. **Run it**
   ```bash
   streamlit run app.py
   ```

## Running tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Tests mock all external API calls — no network access or real API keys needed.
A GitHub Actions workflow (`.github/workflows/tests.yml`) runs the same suite
on every push and pull request.

## Evolution

This project started as a Jupyter notebook prototype (`legacy/final_code.ipynb`)
using [Ollama](https://ollama.com) to run an LLM locally, with `pyttsx3` for
offline text-to-speech. It later grew a Streamlit front end
(`legacy/streamlit_ollama_prototype.py`) with Deepgram handling both speech-to-text
and text-to-speech, while the LLM stayed local via Ollama.

The current version drops the local LLM entirely in favor of **Groq**:
- No GPU or multi-GB model download required
- Fast enough for natural back-and-forth conversation on a laptop with no
  dedicated graphics card
- Deployable as a live web demo (a locally-run Ollama instance can't be)

The original prototypes are kept in `legacy/` (API keys redacted) as a record
of how the project evolved.

## Tech stack

Streamlit · Deepgram (STT + TTS) · Groq (LLM) · sounddevice · pytest
