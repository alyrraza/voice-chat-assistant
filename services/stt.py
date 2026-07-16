"""Live microphone capture + streaming speech-to-text via Deepgram."""
import asyncio
import json
import queue
import threading

import sounddevice as sd
import websockets

from . import config


class VoiceRecorder:
    """Captures mic audio on a background thread and streams it to Deepgram.

    Usage: call start(), speak, call stop() to get the final transcript.
    Runs its own asyncio loop on a daemon thread so it doesn't block Streamlit.
    """

    def __init__(self):
        self._audio_queue: queue.Queue = queue.Queue()
        self._transcript_queue: queue.Queue = queue.Queue()
        self._recording = threading.Event()
        self._thread: threading.Thread | None = None
        self._error: str | None = None

    @property
    def is_recording(self) -> bool:
        return self._recording.is_set()

    def start(self) -> None:
        if self._recording.is_set():
            return
        self._error = None
        self._recording.set()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> str:
        """Stops recording and returns the full transcript collected so far."""
        self._recording.clear()
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

        fragments = []
        while not self._transcript_queue.empty():
            fragments.append(self._transcript_queue.get_nowait())
        return " ".join(fragments).strip()

    @property
    def error(self) -> str | None:
        return self._error

    def _run(self) -> None:
        try:
            asyncio.run(self._stream())
        except Exception as e:
            self._error = str(e)

    def _audio_callback(self, indata, frames, time_info, status):
        if self._recording.is_set():
            self._audio_queue.put(bytes(indata))

    async def _stream(self) -> None:
        headers = {"Authorization": f"token {config.DEEPGRAM_API_KEY}"}
        async with websockets.connect(
            config.DEEPGRAM_STT_URL, additional_headers=headers
        ) as ws:
            with sd.RawInputStream(
                samplerate=config.SAMPLE_RATE,
                blocksize=1024,
                channels=config.CHANNELS,
                dtype="int16",
                callback=self._audio_callback,
            ):
                await asyncio.gather(self._sender(ws), self._receiver(ws))

    async def _sender(self, ws) -> None:
        while self._recording.is_set():
            try:
                data = self._audio_queue.get_nowait()
                await ws.send(data)
            except queue.Empty:
                await asyncio.sleep(0.05)

    async def _receiver(self, ws) -> None:
        while self._recording.is_set():
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=0.5)
            except asyncio.TimeoutError:
                continue
            except websockets.exceptions.ConnectionClosed:
                break

            msg = json.loads(raw)
            transcript = (
                msg.get("channel", {})
                .get("alternatives", [{}])[0]
                .get("transcript", "")
            )
            if transcript:
                self._transcript_queue.put(transcript)
