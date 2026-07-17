# 🎙️ Voice Chat Assistant

A real-time voice assistant: speak, get a live transcript, a conversational
LLM reply, and a spoken response back — entirely via cloud APIs, no local
models or GPU required.

**Speech-to-text → LLM → Text-to-speech.**

The project ships as **two frontends over the same backend logic**:

| Flavor | Frontend | Mic capture | Deployable live? |
|---|---|---|---|
| **Local** | Streamlit (`app.py`) | Server-side (`sounddevice`) | No — mic is on whatever machine runs the server |
| **Web** | React + Vite (`frontend/`) | Browser (`MediaRecorder`) | Yes — deployed on Vercel |

Server-side mic capture only works when "server" and "your laptop" are the
same machine. The React/Vercel flavor records audio in the *visitor's*
browser instead, so it works for anyone hitting the live URL — see
[Evolution](#evolution) for why both exist.

## Features

- 🎤 Voice recording (one-click record/stop, in-browser for the web flavor)
- ⌨️ Text input fallback — type instead of speak, useful for demos
- 💬 Full conversational memory (the assistant sees the whole chat history, not just your last message)
- 🔊 Spoken replies, autoplayed
- 🛡️ Retry-with-backoff on external API calls, structured logging, and a unit test suite

## Architecture

```
Streamlit flavor (local):
🎤 Mic ──(sounddevice)──▶ Deepgram STT (websocket, streaming) ──▶ Groq LLM ──▶ Deepgram TTS ──▶ 🔊

React/Vercel flavor (live):
🎤 Mic ──(browser MediaRecorder)──▶ POST /api/backend?action=transcribe ──▶ Deepgram STT (prerecorded)
                                                                                    │
                            POST /api/backend?action=chat {messages} ──▶ Groq LLM ◀──┘
                                          │
                            POST /api/backend?action=speak {text} ──▶ Deepgram TTS ──▶ 🔊
```

`frontend/api/backend.py` is the Vercel Python serverless function — it lives
*inside* `frontend/` (Vercel's Root Directory for this project) so it
deploys correctly regardless of monorepo routing quirks, and is
deliberately self-contained (no import from the repo-root `services/`
package) so it has zero cross-directory dependencies. It routes internally
by the `action` query param rather than being three separate files.

| File | Responsibility | Used by |
|---|---|---|
| `services/config.py` | Loads API keys/settings from env | Streamlit |
| `services/stt.py` | Mic capture + streaming speech-to-text | Streamlit |
| `services/stt_batch.py` | Prerecorded speech-to-text (no mic access needed) | Streamlit (reference) |
| `services/llm.py` | Chat completion via Groq | Streamlit |
| `services/tts.py` | Text-to-speech via Deepgram | Streamlit |
| `services/retry.py` | Retry-with-backoff decorator for flaky external calls | Streamlit |
| `services/logging_config.py` | One-line structured logging setup | Streamlit |
| `app.py` | Streamlit UI | Streamlit flavor |
| `frontend/api/backend.py` | Self-contained Vercel Python function (chat/transcribe/speak routes) | Web flavor |
| `frontend/` | Vite + React UI | Web flavor |

## Run locally (Streamlit flavor)

1. **Clone the repo**
   ```bash
   git clone https://github.com/alyrraza/voice-chat-assistant.git
   cd voice-chat-assistant
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate      # Windows
   source .venv/bin/activate   # macOS/Linux
   ```

3. **Install dependencies and add API keys**
   ```bash
   pip install -r requirements.txt
   ```
   Copy `.env.example` to `.env` and fill in:
   - `DEEPGRAM_API_KEY` — free at [console.deepgram.com](https://console.deepgram.com)
   - `GROQ_API_KEY` — free at [console.groq.com/keys](https://console.groq.com/keys)

4. **Run it**
   ```bash
   streamlit run app.py
   ```

## Run locally (React flavor)

```bash
cd frontend
npm install
npm run dev
```

Voice recording needs the `/api/*` endpoints, so for a fully working local
preview use the [Vercel CLI](https://vercel.com/docs/cli)'s `vercel dev`
from inside `frontend/` instead — it runs the React app and the Python
function together.

## Deploy the React flavor on Vercel

1. Go to [vercel.com/new](https://vercel.com/new) and import this GitHub repo.
2. In **Project Settings → General → Root Directory**, set it to `frontend`.
   This is required — `frontend/` has its own `package.json` (for the Vite
   build) and `frontend/api/backend.py` (the serverless function), and Vercel
   needs Root Directory pointed there to pick both up automatically.
3. In **Project Settings → Environment Variables**, add `DEEPGRAM_API_KEY`
   and `GROQ_API_KEY` (same keys as your local `.env`).
4. Deploy — no `vercel.json` needed; Vercel auto-detects the Vite frontend
   and the Python function once Root Directory is set correctly.

## Running tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Tests mock all external API calls — no network access or real API keys
needed. A GitHub Actions workflow (`.github/workflows/tests.yml`) runs the
same suite on every push and pull request.

## Evolution

This project started as a Jupyter notebook prototype (`legacy/final_code.ipynb`)
using [Ollama](https://ollama.com) to run an LLM locally, with `pyttsx3` for
offline text-to-speech. It later grew a Streamlit front end
(`legacy/streamlit_ollama_prototype.py`) with Deepgram handling both speech-to-text
and text-to-speech, while the LLM stayed local via Ollama.

The next version (`app.py`) dropped the local LLM for **Groq** — no GPU or
multi-GB model download required, and fast enough for natural conversation
on a laptop with no dedicated graphics card. But it still captured audio
server-side via `sounddevice`, which only works when the server *is* your
own laptop — not something you can put a link to.

The current web flavor (`frontend/`) fixes that: the browser records audio
(so it works for anyone visiting the deployed site) and a single stateless
Vercel Python function (`frontend/api/backend.py`) handles STT/LLM/TTS,
built on the same STT/LLM/TTS logic the Streamlit app already proved out.

The original prototypes are kept in `legacy/` (API keys redacted) as a
record of how the project evolved.

## Tech stack

Streamlit · React · Vite · Vercel (serverless Python functions) · Deepgram (STT + TTS) · Groq (LLM) · sounddevice · pytest
