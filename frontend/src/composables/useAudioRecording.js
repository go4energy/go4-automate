import { ref } from 'vue'

export function useAudioRecording() {
  const isRecording = ref(false)
  const error = ref(null)

  let mediaRecorder = null
  let chunks = []

  async function startRecording() {
    error.value = null
    chunks = []

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      mediaRecorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
          ? 'audio/webm;codecs=opus'
          : 'audio/webm',
      })

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.push(e.data)
      }

      mediaRecorder.start()
      isRecording.value = true
    } catch (err) {
      error.value = err.message || 'Mikrofon-Zugriff verweigert'
    }
  }

  function stopRecording() {
    return new Promise((resolve) => {
      if (!mediaRecorder || mediaRecorder.state === 'inactive') {
        isRecording.value = false
        resolve(null)
        return
      }

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunks, { type: 'audio/webm' })
        // Stop all tracks
        mediaRecorder.stream.getTracks().forEach((t) => t.stop())
        mediaRecorder = null
        chunks = []
        isRecording.value = false
        resolve(blob)
      }

      mediaRecorder.stop()
    })
  }

  return { isRecording, error, startRecording, stopRecording }
}
