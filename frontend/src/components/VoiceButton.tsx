import { useRef, useState } from 'react'

/**
 * A mic button that transcribes speech using the browser-native Web Speech API
 * (SpeechRecognition). Renders nothing if the browser doesn't support it
 * (support is mainly Chromium-based browsers over https/localhost).
 */
interface SpeechRecognitionLike {
  lang: string
  interimResults: boolean
  onresult: (e: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void
  onend: () => void
  onerror: () => void
  start: () => void
  stop: () => void
}

type SRCtor = new () => SpeechRecognitionLike

function getCtor(): SRCtor | null {
  const w = window as unknown as {
    SpeechRecognition?: SRCtor
    webkitSpeechRecognition?: SRCtor
  }
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null
}

export default function VoiceButton({
  onResult,
}: {
  onResult: (text: string) => void
}) {
  const [listening, setListening] = useState(false)
  const recRef = useRef<SpeechRecognitionLike | null>(null)
  const Ctor = getCtor()
  if (!Ctor) return null

  function toggle() {
    if (listening) {
      recRef.current?.stop()
      return
    }
    const rec = new Ctor!()
    rec.lang = 'en-US'
    rec.interimResults = false
    rec.onresult = (e) => {
      const text = e.results[0]?.[0]?.transcript ?? ''
      if (text) onResult(text)
    }
    rec.onend = () => setListening(false)
    rec.onerror = () => setListening(false)
    recRef.current = rec
    setListening(true)
    rec.start()
  }

  return (
    <button
      type="button"
      className={`btn voice ${listening ? 'voice--on' : ''}`}
      onClick={toggle}
      title="Search by voice"
      aria-label="Search by voice"
    >
      {listening ? '● listening…' : '🎤'}
    </button>
  )
}
