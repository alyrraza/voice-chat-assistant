import streamlit as st
import asyncio
import websockets
import json
import base64
import pyaudio
import threading
import queue
import time
import requests
import sounddevice as sd
import numpy as np
from streamlit.runtime.scriptrunner import add_script_run_ctx
from langchain.llms import Ollama




# Initialize Ollama
try:
    ollama = Ollama(base_url='http://localhost:11434', model='llama3.2:1b')
    print("Successfully initialized Ollama")
except Exception as e:
    print(f"Error initializing Ollama: {e}")

# Deepgram API key
# NOTE: the original key that lived here has been revoked/redacted before
# this project was made public. See services/config.py for the current,
# env-var-based approach used by the rebuilt app.
DEEPGRAM_API_KEY = "<REDACTED>"
wss_url = 'wss://api.deepgram.com/v1/listen?encoding=linear16&sample_rate=16000&channels=1&punctuate=true&model=general'

# Deepgram TTS configuration
DEEPGRAM_TTS_URL = "https://api.deepgram.com/v1/speak"
TTS_HEADERS = {
    "Authorization": f"Token {DEEPGRAM_API_KEY}",
    "Content-Type": "application/json"
}



# PyAudio configuration
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1024

# Shared variables
audio_queue = queue.Queue()
recording_flag = threading.Event()
transcription_queue = queue.Queue()

# Initialize session state
if "transcriptions" not in st.session_state:
    st.session_state.transcriptions = []
if "responses" not in st.session_state:
    st.session_state.responses = []
if "is_recording" not in st.session_state:
    st.session_state.is_recording = False
if "is_processing" not in st.session_state:
    st.session_state.is_processing = False
if "update_counter" not in st.session_state:
    st.session_state.update_counter = 0
if "current_transcription" not in st.session_state:
    st.session_state.current_transcription = ""
if "current_session_text" not in st.session_state:
    st.session_state.current_session_text = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [{"role": "system", "content": "You are a helpful assistant. Respond concisely and keep the conversation flowing."}]
if "tts_enabled" not in st.session_state:
    st.session_state.tts_enabled = True
if "last_audio_response" not in st.session_state:
    st.session_state.last_audio_response = None

# Add custom CSS for chat bubbles
CHAT_CSS = """
<style>
.chat-container {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 20px;
    height: 500px;
    overflow-y: auto;
    background: #f5f7fa;
    border-radius: 10px;
    margin: 10px 0;
}

.message {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    max-width: 80%;
}

.user-message {
    margin-right: auto;
}

.assistant-message {
    margin-left: auto;
    flex-direction: row-reverse;
}

.message-bubble {
    padding: 12px 16px;
    border-radius: 15px;
    font-size: 15px;
    line-height: 1.4;
}

.user-bubble {
    background: #007AFF;
    color: white;
}

.assistant-bubble {
    background: white;
    color: black;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: #E0E0E0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
}

.recording-indicator {
    color: #FF4B4B;
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 10px 0;
}

.controls-container {
    background: white;
    padding: 15px;
    border-radius: 10px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    margin: 10px 0;
}
</style>
"""

WAVE_HTML = """
<style>
.wave-container {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 5px;
    height: 30px;
    width: 400px;
    margin: 10px auto;
    background: linear-gradient(135deg, #f5f7fa 0%, #e4e9f2 100%);
    border-radius: 12px;
    padding: 7px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.wave {
    width: 4px;
    height: 25px;
    background: linear-gradient(45deg, #4776E6, #8E54E9);
    border-radius: 3px;
    animation: wave 1s infinite ease-in-out;
    display: inline-block;
}

@keyframes wave {
    0%, 100% { transform: scaleY(0.5); }
    40% { transform: scaleY(1.5); }
}

.wave:nth-child(1) { animation-delay: 0.0s; }
.wave:nth-child(2) { animation-delay: 0.1s; }
.wave:nth-child(3) { animation-delay: 0.2s; }
.wave:nth-child(4) { animation-delay: 0.3s; }
.wave:nth-child(5) { animation-delay: 0.4s; }
.wave:nth-child(6) { animation-delay: 0.5s; }
.wave:nth-child(7) { animation-delay: 0.6s; }
.wave:nth-child(8) { animation-delay: 0.7s; }
.wave:nth-child(9) { animation-delay: 0.8s; }
.wave:nth-child(10) { animation-delay: 0.9s; }
.wave:nth-child(11) { animation-delay: 1.0s; }
.wave:nth-child(12) { animation-delay: 1.1s; }
.wave:nth-child(13) { animation-delay: 1.2s; }
.wave:nth-child(14) { animation-delay: 1.3s; }
.wave:nth-child(15) { animation-delay: 1.4s; }
</style>

<div class="wave-container">
    <div class="wave"></div>
    <div class="wave"></div>
    <div class="wave"></div>
    <div class="wave"></div>
    <div class="wave"></div>
    <div class="wave"></div>
    <div class="wave"></div>
    <div class="wave"></div>
    <div class="wave"></div>
    <div class="wave"></div>
    <div class="wave"></div>
    <div class="wave"></div>
    <div class="wave"></div>
    <div class="wave"></div>
    <div class="wave"></div>
</div>
"""

def text_to_speech(text):
    """Convert text to speech using Deepgram's TTS API"""
    try:
        payload = {
            "text": text
        }
        
        response = requests.post(DEEPGRAM_TTS_URL, headers=TTS_HEADERS, json=payload)
        
        if response.status_code == 200:
            # Convert audio data to base64
            audio_base64 = base64.b64encode(response.content).decode('utf-8')
            # Create HTML audio element
            audio_html = f"""
                <audio autoplay>
                    <source src="data:audio/wav;base64,{audio_base64}" type="audio/wav">
                    Your browser does not support the audio element.
                </audio>
            """
            return audio_html
        else:
            print(f"TTS API error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"Error in text_to_speech: {e}")
        return None




def replay_last_response():
    """Replay the last audio response"""
    if st.session_state.last_audio_response:
        st.components.v1.html(st.session_state.last_audio_response, height=50)
        
        
def capture_audio():
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    
    while st.session_state.is_recording:
        try:
            data = stream.read(CHUNK, exception_on_overflow=False)
            audio_queue.put(data)
        except Exception as e:
            print(f"Error capturing audio: {e}")
    
    stream.stop_stream()
    stream.close()
    p.terminate()

async def handle_deepgram():
    headers = {'Authorization': f'token {DEEPGRAM_API_KEY}'}
    
    async with websockets.connect(wss_url, extra_headers=headers) as ws:
        async def send_audio():
            while st.session_state.is_recording:
                if not audio_queue.empty():
                    data = audio_queue.get()
                    await ws.send(data)
                await asyncio.sleep(0.001)
        
        async def receive_transcriptions():
            while st.session_state.is_recording:
                try:
                    msg = await ws.recv()
                    res = json.loads(msg)
                    if 'channel' in res:
                        text = res['channel']['alternatives'][0]['transcript']
                        if text.strip():
                            print(f"Received text: {text}")
                            st.session_state.current_session_text.append(text)
                            st.session_state.current_transcription = " ".join(st.session_state.current_session_text)
                            st.session_state.update_counter += 1
                            st.rerun()
                except Exception as e:
                    print(f"Error receiving: {e}")
        
        await asyncio.gather(send_audio(), receive_transcriptions())

def get_ai_response(text):
    """Get response from LLaMA and convert to speech"""
    print(f"\nSending to LLaMA: {text}")
    st.session_state.is_processing = True
    
    try:
        # Add user message to chat history
        st.session_state.chat_history.append({"role": "user", "content": text})
        
        # Get response from LLaMA
        print("Waiting for LLaMA response...")
        response = ollama.invoke(text)
        print(f"Received LLaMA response: {response}")
        
        # Add assistant response to chat history
        st.session_state.chat_history.append({"role": "assistant", "content": response})
        
        # Convert response to speech if enabled
        if st.session_state.tts_enabled:
            print("Converting response to speech...")
            audio_html = text_to_speech(response)
            
            if audio_html:
                # Store the audio HTML
                st.session_state.last_audio_response = audio_html
                # Display the audio element
                st.components.v1.html(audio_html, height=50)
        
        return response
    except Exception as e:
        print(f"Error getting AI response: {e}")
        return f"Sorry, I couldn't process that input. Error: {str(e)}"
    finally:
        st.session_state.is_processing = False
        
        
def start_recording():
    st.session_state.is_recording = True
    st.session_state.current_session_text = []
    st.session_state.current_transcription = ""
    print("\nStarted recording...")
    
    # Start audio capture thread
    audio_thread = threading.Thread(target=capture_audio)
    add_script_run_ctx(audio_thread)
    audio_thread.start()
    
    # Start websocket handling thread
    ws_thread = threading.Thread(target=lambda: asyncio.run(handle_deepgram()))
    add_script_run_ctx(ws_thread)
    ws_thread.start()

def stop_recording():
    if st.session_state.is_recording:
        print("\nStopped recording")
        st.session_state.is_recording = False
        if st.session_state.current_transcription.strip():
            print(f"Final transcription: {st.session_state.current_transcription}")
            # Add transcription to history
            st.session_state.transcriptions.append(st.session_state.current_transcription)
            
            # Get AI response
            response = get_ai_response(st.session_state.current_transcription)
            st.session_state.responses.append(response)
            
        st.session_state.current_transcription = ""
        st.session_state.current_session_text = []

def display_chat_messages():
    messages_html = ""
    
    # Combine transcriptions and responses into conversation flow
    for i in range(max(len(st.session_state.transcriptions), len(st.session_state.responses))):
        # Add user message if available
        if i < len(st.session_state.transcriptions):
            messages_html += f"""
            <div class="message user-message">
                <div class="avatar">👤</div>
                <div class="message-bubble user-bubble">
                    {st.session_state.transcriptions[i]}
                </div>
            </div>
            """
        
        # Add assistant message if available
        if i < len(st.session_state.responses):
            messages_html += f"""
            <div class="message assistant-message">
                <div class="avatar">🤖</div>
                <div class="message-bubble assistant-bubble">
                    {st.session_state.responses[i]}
                </div>
            </div>
            """
    
    # Add current transcription if recording
    if st.session_state.current_transcription:
        messages_html += f"""
        <div class="message user-message">
            <div class="avatar">👤</div>
            <div class="message-bubble user-bubble">
                {st.session_state.current_transcription}
            </div>
        </div>
        """
    
    # Create the chat container
    chat_html = f"""
    {CHAT_CSS}
    <div class="chat-container">
        {messages_html}
    </div>
    """
    
    return chat_html

# Streamlit UI
st.title("Voice Chat Assistant")

# Create a container for TTS controls
# Create a container for TTS controls
with st.container():
    st.markdown('<div class="controls-container">', unsafe_allow_html=True)
    
    # TTS Controls in columns
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.session_state.tts_enabled = st.toggle("Enable Speech", value=True)
    
    with col2:
        if st.button("🔁 Replay Last", use_container_width=True):
            replay_last_response()
    
    st.markdown('</div>', unsafe_allow_html=True)

# Create a container with custom width
container = st.container()
with container:
    # Create columns for buttons with specific widths
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if st.button("🎤 Start", type="primary", use_container_width=True):
            start_recording()

    with col2:
        if st.button("🛑 Stop", type="secondary", use_container_width=True):
            stop_recording()

    with col3:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.transcriptions = []
            st.session_state.responses = []
            st.session_state.current_transcription = ""
            st.session_state.current_session_text = []
            st.session_state.update_counter = 0
            st.session_state.chat_history = [{"role": "system", "content": "You are a helpful assistant. Respond concisely and keep the conversation flowing."}]
            st.session_state.last_audio_response = None

    # Show wave animation during recording
    if st.session_state.is_recording:
        st.components.v1.html(WAVE_HTML, height=70)
        st.markdown('<div class="recording-indicator">🔴 Recording...</div>', unsafe_allow_html=True)

    # Display chat interface
    st.components.v1.html(display_chat_messages(), height=600, scrolling=True)

    # Show processing indicator
    if st.session_state.is_processing:
        st.markdown("*Getting response... ⏳*")