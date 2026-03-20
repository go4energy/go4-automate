<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useAssistantStore } from '@/stores/assistant'

const assistantStore = useAssistantStore()

// State
const connected = ref(false)
const connecting = ref(false)
const recording = ref(false)
const error = ref(null)
const messages = ref([])
const messagesContainer = ref(null)
const currentTranscript = ref('')
const toolStatus = ref(null)

// WebSocket + Audio
let ws = null
let audioContext = null
let mediaStream = null
let mediaProcessor = null
let playbackQueue = []
let isPlayingAudio = false

// Auto-scroll
watch(
  () => messages.value.length,
  async () => {
    await nextTick()
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  },
)

const canConnect = computed(() => !connected.value && !connecting.value)

async function connect() {
  if (connected.value || connecting.value) return
  connecting.value = true
  error.value = null

  try {
    const token = localStorage.getItem('token') || ''
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const url = `${protocol}//${host}/ws/voice-realtime?token=${token}`

    ws = new WebSocket(url)
    ws.onopen = () => {
      connected.value = true
      connecting.value = false
      // Create playback context on user gesture (connect button click)
      playbackCtx = new AudioContext()
      messages.value.push({ role: 'system', text: 'Verbunden. Mikrofon wird aktiviert...' })
      startMicrophone()
    }
    ws.onmessage = handleMessage
    ws.onerror = () => {
      error.value = 'WebSocket Verbindungsfehler'
      connecting.value = false
    }
    ws.onclose = () => {
      connected.value = false
      connecting.value = false
      recording.value = false
      stopMicrophone()
    }
  } catch (err) {
    error.value = err.message
    connecting.value = false
  }
}

function disconnect() {
  stopMicrophone()
  if (ws) {
    ws.close()
    ws = null
  }
  if (playbackCtx && playbackCtx.state !== 'closed') {
    playbackCtx.close()
    playbackCtx = null
  }
  connected.value = false
  recording.value = false
  playbackQueue = []
  isPlayingAudio = false
  nextPlayTime = 0
}

function handleMessage(event) {
  const msg = JSON.parse(event.data)

  switch (msg.type) {
    case 'session.ready':
      messages.value.push({ role: 'system', text: `Realtime Session bereit (${msg.model})` })
      break

    case 'session.created':
    case 'session.updated':
      break

    // User speech transcript
    case 'conversation.item.input_audio_transcription.delta':
      currentTranscript.value += msg.delta || ''
      break

    case 'conversation.item.input_audio_transcription.completed':
      if (msg.transcript) {
        messages.value.push({ role: 'user', text: msg.transcript })
      }
      currentTranscript.value = ''
      break

    // Assistant text transcript
    case 'response.audio_transcript.delta':
      updateAssistantMessage(msg.delta || '')
      break

    case 'response.audio_transcript.done':
      finalizeAssistantMessage()
      break

    // Assistant audio
    case 'response.audio.delta':
      if (msg.delta) {
        enqueueAudio(msg.delta)
      }
      break

    // Tool execution
    case 'tool.executing':
      toolStatus.value = `⚡ ${msg.tool_name}...`
      break

    case 'tool.result':
      toolStatus.value = null
      messages.value.push({
        role: 'tool',
        text: `${msg.tool_name}: ${msg.result}`,
        toolName: msg.tool_name,
      })
      break

    // Function call tracking (for UI)
    case 'response.function_call_arguments.delta':
      break

    case 'error':
      error.value = msg.error?.message || msg.message || 'Unbekannter Fehler'
      break

    case 'response.done':
      toolStatus.value = null
      break
  }
}

// ── Assistant message accumulation ──

let pendingAssistantText = ''
let pendingAssistantIdx = -1

function updateAssistantMessage(delta) {
  pendingAssistantText += delta
  if (pendingAssistantIdx === -1) {
    pendingAssistantIdx = messages.value.length
    messages.value.push({ role: 'assistant', text: pendingAssistantText, streaming: true })
  } else {
    messages.value[pendingAssistantIdx].text = pendingAssistantText
  }
}

function finalizeAssistantMessage() {
  if (pendingAssistantIdx >= 0 && pendingAssistantIdx < messages.value.length) {
    messages.value[pendingAssistantIdx].streaming = false
  }
  pendingAssistantText = ''
  pendingAssistantIdx = -1
}

// ── Microphone capture (PCM16 24kHz) ──

async function startMicrophone() {
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true })
    audioContext = new AudioContext()

    const source = audioContext.createMediaStreamSource(mediaStream)
    const nativeSampleRate = audioContext.sampleRate
    mediaProcessor = audioContext.createScriptProcessor(4096, 1, 1)

    mediaProcessor.onaudioprocess = (event) => {
      if (!connected.value || !ws || ws.readyState !== WebSocket.OPEN) return

      const inputData = event.inputBuffer.getChannelData(0)
      // Resample from native rate to 24kHz for OpenAI
      const resampled = resampleFloat32(inputData, nativeSampleRate, 24000)
      const pcm16 = float32ToPcm16(resampled)
      const base64 = arrayBufferToBase64(pcm16.buffer)

      ws.send(JSON.stringify({
        type: 'input_audio_buffer.append',
        audio: base64,
      }))
    }

    source.connect(mediaProcessor)
    mediaProcessor.connect(audioContext.destination)
    recording.value = true
  } catch (err) {
    error.value = `Mikrofon-Fehler: ${err.message}`
  }
}

function stopMicrophone() {
  if (mediaProcessor) {
    mediaProcessor.disconnect()
    mediaProcessor = null
  }
  if (mediaStream) {
    mediaStream.getTracks().forEach((t) => t.stop())
    mediaStream = null
  }
  if (audioContext && audioContext.state !== 'closed') {
    audioContext.close()
    audioContext = null
  }
  recording.value = false
}

function toggleMute() {
  if (!mediaStream) return
  const track = mediaStream.getAudioTracks()[0]
  if (track) {
    track.enabled = !track.enabled
    recording.value = track.enabled
  }
}

// ── Audio playback (PCM16 24kHz) ──

function enqueueAudio(base64Chunk) {
  const bytes = base64ToArrayBuffer(base64Chunk)
  playbackQueue.push(bytes)
  if (!isPlayingAudio) {
    playNextChunk()
  }
}

let playbackCtx = null
let nextPlayTime = 0

async function playNextChunk() {
  if (playbackQueue.length === 0) {
    isPlayingAudio = false
    return
  }

  isPlayingAudio = true

  if (!playbackCtx || playbackCtx.state === 'closed') {
    playbackCtx = new AudioContext()
  }

  // Resume if suspended (browser autoplay policy)
  if (playbackCtx.state === 'suspended') {
    await playbackCtx.resume()
  }

  // Schedule all queued chunks seamlessly
  while (playbackQueue.length > 0) {
    const pcmData = playbackQueue.shift()
    try {
      const float32 = pcm16ToFloat32(new Int16Array(pcmData))
      const resampled = resampleFloat32(float32, 24000, playbackCtx.sampleRate)
      const buffer = playbackCtx.createBuffer(1, resampled.length, playbackCtx.sampleRate)
      buffer.getChannelData(0).set(resampled)

      const source = playbackCtx.createBufferSource()
      source.buffer = buffer
      source.connect(playbackCtx.destination)

      const now = playbackCtx.currentTime
      const startAt = Math.max(now, nextPlayTime)
      source.start(startAt)
      nextPlayTime = startAt + buffer.duration
    } catch {
      // Skip corrupt chunk
    }
  }

  // Reset when done
  const remaining = nextPlayTime - playbackCtx.currentTime
  if (remaining > 0) {
    setTimeout(() => {
      isPlayingAudio = false
      nextPlayTime = 0
      // Check if more arrived while playing
      if (playbackQueue.length > 0) playNextChunk()
    }, remaining * 1000 + 50)
  } else {
    isPlayingAudio = false
    nextPlayTime = 0
  }
}

// ── Resampling ──

function resampleFloat32(input, fromRate, toRate) {
  if (fromRate === toRate) return input
  const ratio = fromRate / toRate
  const outputLength = Math.round(input.length / ratio)
  const output = new Float32Array(outputLength)
  for (let i = 0; i < outputLength; i++) {
    const srcIdx = i * ratio
    const low = Math.floor(srcIdx)
    const high = Math.min(low + 1, input.length - 1)
    const frac = srcIdx - low
    output[i] = input[low] * (1 - frac) + input[high] * frac
  }
  return output
}

// ── PCM16 ↔ Float32 conversion ──

function float32ToPcm16(float32Array) {
  const pcm16 = new Int16Array(float32Array.length)
  for (let i = 0; i < float32Array.length; i++) {
    const s = Math.max(-1, Math.min(1, float32Array[i]))
    pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff
  }
  return pcm16
}

function pcm16ToFloat32(pcm16Array) {
  const float32 = new Float32Array(pcm16Array.length)
  for (let i = 0; i < pcm16Array.length; i++) {
    float32[i] = pcm16Array[i] / 0x8000
  }
  return float32
}

function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer)
  let binary = ''
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i])
  }
  return btoa(binary)
}

function base64ToArrayBuffer(base64) {
  const binary = atob(base64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i)
  }
  return bytes.buffer
}

onBeforeUnmount(() => {
  disconnect()
})
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- Header -->
    <div class="flex items-center justify-between border-b border-gray-200 px-4 py-3 dark:border-gray-700">
      <div class="flex items-center gap-3">
        <div
          class="h-3 w-3 rounded-full"
          :class="connected ? 'bg-green-500' : 'bg-gray-400'"
        />
        <span class="text-sm font-medium text-gray-700 dark:text-gray-300">
          Realtime Voice
        </span>
        <span
          v-if="recording"
          class="text-xs text-red-500"
        >
          Mikrofon aktiv
        </span>
      </div>
      <div class="flex items-center gap-2">
        <button
          v-if="canConnect"
          class="rounded-lg bg-go4-primary px-4 py-1.5 text-sm text-white hover:bg-go4-primary/90"
          @click="connect"
        >
          Verbinden
        </button>
        <button
          v-if="connected"
          class="rounded-lg bg-gray-200 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-300 dark:bg-gray-600 dark:text-gray-200"
          @click="toggleMute"
        >
          {{ recording ? 'Stumm' : 'Mikrofon an' }}
        </button>
        <button
          v-if="connected"
          class="rounded-lg bg-red-100 px-3 py-1.5 text-sm text-red-700 hover:bg-red-200"
          @click="disconnect"
        >
          Beenden
        </button>
      </div>
    </div>

    <!-- Error -->
    <div
      v-if="error"
      class="bg-red-50 px-4 py-2 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-400"
    >
      {{ error }}
    </div>

    <!-- Messages -->
    <div
      ref="messagesContainer"
      class="flex-1 overflow-y-auto px-4 py-4 space-y-3"
    >
      <div
        v-for="(msg, idx) in messages"
        :key="idx"
        class="flex"
        :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
      >
        <div
          class="max-w-[80%] rounded-xl px-4 py-2 text-sm"
          :class="{
            'bg-go4-primary text-white': msg.role === 'user',
            'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200': msg.role === 'assistant',
            'bg-yellow-50 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300 font-mono text-xs': msg.role === 'tool',
            'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 text-xs': msg.role === 'system',
          }"
        >
          <span
            v-if="msg.streaming"
            class="animate-pulse"
          >{{ msg.text }}...</span>
          <span v-else>{{ msg.text }}</span>
        </div>
      </div>

      <!-- Live transcription -->
      <div
        v-if="currentTranscript"
        class="flex justify-end"
      >
        <div class="max-w-[80%] rounded-xl bg-go4-primary/50 px-4 py-2 text-sm text-white animate-pulse">
          {{ currentTranscript }}...
        </div>
      </div>

      <!-- Tool status -->
      <div
        v-if="toolStatus"
        class="flex justify-start"
      >
        <div class="rounded-xl bg-yellow-50 px-4 py-2 text-xs text-yellow-700 animate-pulse dark:bg-yellow-900/30 dark:text-yellow-300">
          {{ toolStatus }}
        </div>
      </div>
    </div>

    <!-- Connecting overlay -->
    <div
      v-if="connecting"
      class="flex items-center justify-center py-8"
    >
      <span class="text-sm text-gray-500 animate-pulse">Verbinde mit OpenAI Realtime...</span>
    </div>

    <!-- Not connected hint -->
    <div
      v-if="!connected && !connecting"
      class="flex flex-col items-center justify-center py-12 text-center"
    >
      <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
        Klicke "Verbinden" um den Realtime Voice Chat zu starten.
        Dein Mikrofon wird automatisch aktiviert.
      </p>
    </div>
  </div>
</template>
