import { useRef, useState } from 'react'
import './App.css'

const SYSTEM_PROMPT = {
  role: 'system',
  content: 'You are a helpful assistant. Respond concisely and keep the conversation flowing.',
}

function App() {
  const [messages, setMessages] = useState([SYSTEM_PROMPT])
  const [isRecording, setIsRecording] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [error, setError] = useState(null)
  const [typedText, setTypedText] = useState('')
  const [audioUrl, setAudioUrl] = useState(null)

  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])

  async function startRecording() {
    setError(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      chunksRef.current = []

      recorder.ondataavailable = (e) => chunksRef.current.push(e.data)
      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop())
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType })
        handleAudioBlob(blob)
      }

      recorder.start()
      mediaRecorderRef.current = recorder
      setIsRecording(true)
    } catch (e) {
      setError(`Couldn't access microphone: ${e.message}`)
    }
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop()
    setIsRecording(false)
  }

  async function handleAudioBlob(blob) {
    setIsProcessing(true)
    try {
      const res = await fetch('/api/index?action=transcribe', {
        method: 'POST',
        headers: { 'Content-Type': blob.type || 'audio/webm' },
        body: blob,
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Transcription failed')
      await sendMessage(data.transcript)
    } catch (e) {
      setError(e.message)
      setIsProcessing(false)
    }
  }

  async function sendMessage(text) {
    const trimmed = text.trim()
    if (!trimmed) {
      setIsProcessing(false)
      return
    }

    const nextMessages = [...messages, { role: 'user', content: trimmed }]
    setMessages(nextMessages)
    setIsProcessing(true)
    setError(null)

    try {
      const chatRes = await fetch('/api/index?action=chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: nextMessages }),
      })
      const chatData = await chatRes.json()
      if (!chatRes.ok) throw new Error(chatData.error || 'Chat request failed')

      const withReply = [...nextMessages, { role: 'assistant', content: chatData.reply }]
      setMessages(withReply)

      const speakRes = await fetch('/api/index?action=speak', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: chatData.reply }),
      })
      if (speakRes.ok) {
        const audioBlob = await speakRes.blob()
        setAudioUrl((prev) => {
          if (prev) URL.revokeObjectURL(prev)
          return URL.createObjectURL(audioBlob)
        })
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setIsProcessing(false)
    }
  }

  function handleTextSubmit(e) {
    e.preventDefault()
    const text = typedText
    setTypedText('')
    sendMessage(text)
  }

  return (
    <div className="app">
      <header>
        <h1>🎙️ Voice Chat Assistant</h1>
        <p className="subtitle">Speak or type — powered by Groq + Deepgram</p>
      </header>

      <main className="chat">
        {messages
          .filter((m) => m.role !== 'system')
          .map((m, i) => (
            <div key={i} className={`bubble-row ${m.role}`}>
              <div className={`bubble ${m.role}`}>{m.content}</div>
            </div>
          ))}
        {isProcessing && <div className="bubble-row assistant"><div className="bubble assistant thinking">Thinking...</div></div>}
      </main>

      {error && <div className="error-banner">{error}</div>}

      <form className="controls" onSubmit={handleTextSubmit}>
        <button
          type="button"
          className={`record-btn ${isRecording ? 'recording' : ''}`}
          onClick={isRecording ? stopRecording : startRecording}
          disabled={isProcessing}
        >
          {isRecording ? '🛑 Stop' : '🎤 Record'}
        </button>
        <input
          type="text"
          placeholder="Or type a message..."
          value={typedText}
          onChange={(e) => setTypedText(e.target.value)}
          disabled={isProcessing || isRecording}
        />
        <button type="submit" disabled={isProcessing || isRecording || !typedText.trim()}>
          Send
        </button>
      </form>

      {audioUrl && <audio key={audioUrl} src={audioUrl} autoPlay />}
    </div>
  )
}

export default App
