import { ref } from 'vue'

export function useAudioPlayback() {
  const isPlaying = ref(false)

  let currentAudio = null

  function playBase64Audio(base64) {
    return new Promise((resolve) => {
      stop()

      const byteChars = atob(base64)
      const bytes = new Uint8Array(byteChars.length)
      for (let i = 0; i < byteChars.length; i++) {
        bytes[i] = byteChars.charCodeAt(i)
      }
      const blob = new Blob([bytes], { type: 'audio/wav' })
      const url = URL.createObjectURL(blob)

      currentAudio = new Audio(url)
      currentAudio.onended = () => {
        isPlaying.value = false
        URL.revokeObjectURL(url)
        currentAudio = null
        resolve()
      }
      currentAudio.onerror = () => {
        isPlaying.value = false
        URL.revokeObjectURL(url)
        currentAudio = null
        resolve()
      }

      isPlaying.value = true
      currentAudio.play()
    })
  }

  function stop() {
    if (currentAudio) {
      currentAudio.pause()
      currentAudio = null
      isPlaying.value = false
    }
  }

  return { isPlaying, playBase64Audio, stop }
}
