"""Voice Chat Assistant — Streamlit UI.

Speak (or type) -> Deepgram speech-to-text -> Groq LLM -> Deepgram
text-to-speech. See services/ for the individual integrations.
"""
import streamlit as st

from services import config, llm, tts
from services.stt import VoiceRecorder

st.set_page_config(page_title="Voice Chat Assistant", page_icon="🎙️", layout="centered")

STYLE = """
<style>
.wave-container {
    display: flex; justify-content: center; align-items: center; gap: 5px;
    height: 30px; margin: 10px auto; background: linear-gradient(135deg, #f5f7fa 0%, #e4e9f2 100%);
    border-radius: 12px; padding: 7px;
}
.wave {
    width: 4px; height: 25px; background: linear-gradient(45deg, #4776E6, #8E54E9);
    border-radius: 3px; animation: wave 1s infinite ease-in-out; display: inline-block;
}
@keyframes wave { 0%, 100% { transform: scaleY(0.4); } 40% { transform: scaleY(1.4); } }
.wave:nth-child(2) { animation-delay: 0.1s; }
.wave:nth-child(3) { animation-delay: 0.2s; }
.wave:nth-child(4) { animation-delay: 0.3s; }
.wave:nth-child(5) { animation-delay: 0.4s; }
.wave:nth-child(6) { animation-delay: 0.5s; }
.wave:nth-child(7) { animation-delay: 0.6s; }
.wave:nth-child(8) { animation-delay: 0.7s; }
</style>
"""

WAVE_HTML = """
<div class="wave-container">
    <div class="wave"></div><div class="wave"></div><div class="wave"></div>
    <div class="wave"></div><div class="wave"></div><div class="wave"></div>
    <div class="wave"></div><div class="wave"></div>
</div>
"""

SYSTEM_PROMPT = {
    "role": "system",
    "content": "You are a helpful assistant. Respond concisely and keep the conversation flowing.",
}


def init_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = [SYSTEM_PROMPT]
    if "recorder" not in st.session_state:
        st.session_state.recorder = VoiceRecorder()
    if "tts_enabled" not in st.session_state:
        st.session_state.tts_enabled = True
    if "last_audio_html" not in st.session_state:
        st.session_state.last_audio_html = None


def handle_user_message(text: str) -> None:
    text = text.strip()
    if not text:
        return

    st.session_state.messages.append({"role": "user", "content": text})

    with st.spinner("Thinking..."):
        try:
            reply = llm.get_reply(st.session_state.messages)
        except Exception as e:
            reply = f"Sorry, I couldn't reach the assistant right now. ({e})"

    st.session_state.messages.append({"role": "assistant", "content": reply})

    if st.session_state.tts_enabled:
        try:
            st.session_state.last_audio_html = tts.synthesize_html(reply)
        except Exception:
            st.session_state.last_audio_html = None


def render_sidebar() -> None:
    with st.sidebar:
        st.header("⚙️ Setup")
        missing = config.missing_keys()
        if missing:
            st.error("Missing: " + ", ".join(missing))
            st.caption("Add these to a `.env` file in the project root — see `.env.example`.")
        else:
            st.success("API keys loaded")

        st.divider()
        st.caption(f"**LLM:** Groq · `{config.GROQ_MODEL}`")
        st.caption("**STT / TTS:** Deepgram")
        st.session_state.tts_enabled = st.toggle("Enable spoken replies", value=st.session_state.tts_enabled)

        st.divider()
        if st.button("🗑️ Clear conversation", use_container_width=True):
            st.session_state.messages = [SYSTEM_PROMPT]
            st.session_state.last_audio_html = None
            st.rerun()


def render_chat() -> None:
    for msg in st.session_state.messages:
        if msg["role"] == "system":
            continue
        avatar = "🧑" if msg["role"] == "user" else "🤖"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])


def render_controls() -> None:
    missing = bool(config.missing_keys())
    recorder: VoiceRecorder = st.session_state.recorder

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🎤 Start", type="primary", use_container_width=True,
                      disabled=missing or recorder.is_recording):
            recorder.start()
            st.rerun()
    with col2:
        if st.button("🛑 Stop", use_container_width=True, disabled=not recorder.is_recording):
            transcript = recorder.stop()
            if recorder.error:
                st.error(f"Recording error: {recorder.error}")
            handle_user_message(transcript)
            st.rerun()
    with col3:
        if st.button("🔁 Replay last", use_container_width=True,
                      disabled=not st.session_state.last_audio_html):
            st.components.v1.html(st.session_state.last_audio_html, height=50)

    if recorder.is_recording:
        st.markdown(WAVE_HTML, unsafe_allow_html=True)
        st.caption("🔴 Recording... click Stop when you're done speaking.")

    typed = st.chat_input("Or type a message instead of speaking...")
    if typed:
        handle_user_message(typed)
        st.rerun()

    if st.session_state.last_audio_html:
        st.components.v1.html(st.session_state.last_audio_html, height=0)


st.markdown(STYLE, unsafe_allow_html=True)
init_state()
render_sidebar()

st.title("🎙️ Voice Chat Assistant")
st.caption("Speak or type — powered by Groq + Deepgram, no local models required.")

render_chat()
render_controls()
