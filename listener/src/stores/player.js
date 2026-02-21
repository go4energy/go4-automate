import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

export const usePlayerStore = defineStore('player', () => {
  const currentEpisode = ref(null)
  const playing = ref(false)
  const currentTime = ref(0)
  const duration = ref(0)
  const playbackRate = ref(1)
  const audioElement = ref(null)

  const progress = computed(() => {
    if (!duration.value) return 0
    return (currentTime.value / duration.value) * 100
  })

  const timeLeft = computed(() => {
    return Math.max(0, duration.value - currentTime.value)
  })

  function play(episode) {
    currentEpisode.value = episode

    if (!audioElement.value) {
      audioElement.value = new Audio()
      audioElement.value.addEventListener('timeupdate', () => {
        currentTime.value = audioElement.value.currentTime
      })
      audioElement.value.addEventListener('loadedmetadata', () => {
        duration.value = audioElement.value.duration
      })
      audioElement.value.addEventListener('ended', () => {
        playing.value = false
      })
    }

    const audioUrl = episode.audio_url ? `/api/v1/listen/episodes/${episode.id}/audio` : null

    if (!audioUrl) return

    audioElement.value.src = audioUrl
    audioElement.value.playbackRate = playbackRate.value
    audioElement.value.play()
    playing.value = true
  }

  function togglePlay() {
    if (!audioElement.value) return
    if (playing.value) {
      audioElement.value.pause()
    } else {
      audioElement.value.play()
    }
    playing.value = !playing.value
  }

  function seek(time) {
    if (!audioElement.value) return
    audioElement.value.currentTime = time
  }

  function skip(seconds) {
    if (!audioElement.value) return
    audioElement.value.currentTime = Math.min(
      duration.value,
      Math.max(0, audioElement.value.currentTime + seconds)
    )
  }

  function setRate(rate) {
    playbackRate.value = rate
    if (audioElement.value) {
      audioElement.value.playbackRate = rate
    }
  }

  function stop() {
    if (audioElement.value) {
      audioElement.value.pause()
      audioElement.value.src = ''
    }
    playing.value = false
    currentEpisode.value = null
    currentTime.value = 0
    duration.value = 0
  }

  return {
    currentEpisode,
    playing,
    currentTime,
    duration,
    playbackRate,
    progress,
    timeLeft,
    play,
    togglePlay,
    seek,
    skip,
    setRate,
    stop
  }
})
