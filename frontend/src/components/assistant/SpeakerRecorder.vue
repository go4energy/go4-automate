<script setup>
import { ref, onBeforeUnmount } from 'vue'
import { useAssistantStore } from '@/stores/assistant'

const store = useAssistantStore()

const isRecording = ref(false)
const recordingTime = ref(0)
const speakerName = ref('')
const previewUrl = ref(null)
const wavBlob = ref(null)
const uploading = ref(false)
const error = ref(null)
const success = ref(null)

let mediaRecorder = null
let chunks = []
let timerInterval = null
let audioContext = null

async function startRecording() {
  error.value = null
  success.value = null
  chunks = []
  recordingTime.value = 0
  clearPreview()

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    mediaRecorder = new MediaRecorder(stream)
    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunks.push(e.data)
    }
    mediaRecorder.start()
    isRecording.value = true
    timerInterval = setInterval(() => {
      recordingTime.value++
      if (recordingTime.value >= 30) stopRecording()
    }, 1000)
  } catch (err) {
    error.value = err.message || 'Mikrofon-Zugriff verweigert'
  }
}

async function stopRecording() {
  if (!mediaRecorder || mediaRecorder.state === 'inactive') return
  return new Promise((resolve) => {
    mediaRecorder.onstop = async () => {
      clearInterval(timerInterval)
      mediaRecorder.stream.getTracks().forEach((t) => t.stop())
      isRecording.value = false
      const webmBlob = new Blob(chunks, { type: 'audio/webm' })
      chunks = []
      try {
        wavBlob.value = await convertToWav(webmBlob)
        previewUrl.value = URL.createObjectURL(wavBlob.value)
      } catch (err) {
        error.value = 'Konvertierung fehlgeschlagen: ' + err.message
      }
      resolve()
    }
    mediaRecorder.stop()
  })
}

async function convertToWav(blob) {
  audioContext = new (window.AudioContext || window.webkitAudioContext)()
  const arrayBuffer = await blob.arrayBuffer()
  const audioBuffer = await audioContext.decodeAudioData(arrayBuffer)
  const targetRate = 22050
  const offlineCtx = new OfflineAudioContext(1, audioBuffer.duration * targetRate, targetRate)
  const source = offlineCtx.createBufferSource()
  source.buffer = audioBuffer
  source.connect(offlineCtx.destination)
  source.start()
  const rendered = await offlineCtx.startRendering()
  const samples = rendered.getChannelData(0)
  const wavBuffer = encodeWav(samples, targetRate)
  return new Blob([wavBuffer], { type: 'audio/wav' })
}

function encodeWav(samples, sampleRate) {
  const len = samples.length
  const buffer = new ArrayBuffer(44 + len * 2)
  const view = new DataView(buffer)
  writeString(view, 0, 'RIFF')
  view.setUint32(4, 36 + len * 2, true)
  writeString(view, 8, 'WAVE')
  writeString(view, 12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, 1, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true)
  view.setUint16(32, 2, true)
  view.setUint16(34, 16, true)
  writeString(view, 36, 'data')
  view.setUint32(40, len * 2, true)
  let offset = 44
  for (let i = 0; i < len; i++, offset += 2) {
    const s = Math.max(-1, Math.min(1, samples[i]))
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true)
  }
  return buffer
}

function writeString(view, offset, str) {
  for (let i = 0; i < str.length; i++) {
    view.setUint8(offset + i, str.charCodeAt(i))
  }
}

async function handleUpload() {
  if (!wavBlob.value || !speakerName.value.trim()) {
    error.value = 'Bitte Name eingeben und Aufnahme machen'
    return
  }
  uploading.value = true
  error.value = null
  try {
    await store.uploadSpeakerVoice(speakerName.value.trim(), wavBlob.value)
    success.value = `Stimme "${speakerName.value}" gespeichert`
    speakerName.value = ''
    clearPreview()
  } catch (err) {
    error.value = err.message || 'Speichern fehlgeschlagen'
  } finally {
    uploading.value = false
  }
}

function clearPreview() {
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = null
  }
  wavBlob.value = null
}

async function handleDelete(name) {
  try {
    await store.removeSpeakerVoice(name)
  } catch (err) {
    error.value = err.message || 'Loeschen fehlgeschlagen'
  }
}

function formatDuration(seconds) {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

onBeforeUnmount(() => {
  clearInterval(timerInterval)
  clearPreview()
  if (audioContext) audioContext.close()
})
</script>

<template>
  <div class="space-y-5">
    <!-- ① Record button (prominent, top) -->
    <div class="flex flex-col items-center gap-3">
      <button
        class="flex h-16 w-16 items-center justify-center rounded-full transition"
        :class="
          isRecording
            ? 'bg-red-500 text-white animate-pulse shadow-lg shadow-red-500/30'
            : 'bg-go4-primary text-white hover:bg-go4-primary/90 shadow-md'
        "
        @click="isRecording ? stopRecording() : startRecording()"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-7 w-7"
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            v-if="!isRecording"
            fill-rule="evenodd"
            d="M7 4a3 3 0 016 0v4a3 3 0 11-6 0V4zm4 10.93A7.001 7.001 0 0017 8a1 1 0 10-2 0A5 5 0 015 8a1 1 0 00-2 0 7.001 7.001 0 006 6.93V17H6a1 1 0 100 2h8a1 1 0 100-2h-3v-2.07z"
            clip-rule="evenodd"
          />
          <path
            v-else
            fill-rule="evenodd"
            d="M10 18a8 8 0 100-16 8 8 0 000 16zM8 7a1 1 0 00-1 1v4a1 1 0 001 1h4a1 1 0 001-1V8a1 1 0 00-1-1H8z"
            clip-rule="evenodd"
          />
        </svg>
      </button>
      <span
        v-if="isRecording"
        class="text-sm font-medium text-red-500"
      >
        Aufnahme laeuft... {{ formatDuration(recordingTime) }}
      </span>
      <span
        v-else
        class="text-xs text-go4-muted dark:text-gray-400"
      >
        Zum Aufnehmen klicken
      </span>
    </div>

    <!-- ② Vorlesetext -->
    <div class="rounded-lg bg-go4-surface px-4 py-3 dark:bg-gray-900">
      <p class="text-xs font-medium text-go4-muted dark:text-gray-400">
        Lies diesen Text vor:
      </p>
      <p class="mt-1 text-sm leading-relaxed text-go4-secondary dark:text-gray-200">
        &laquo;Guten Morgen, ich habe deine E-Mails durchgesehen. Es gibt drei neue Nachrichten, davon eine dringende von deinem Projektleiter. Soll ich sie dir vorlesen?&raquo;
      </p>
    </div>

    <!-- ③ Audio Preview (nach Aufnahme) -->
    <div
      v-if="previewUrl"
      class="space-y-3"
    >
      <div class="flex items-center gap-2">
        <audio
          :src="previewUrl"
          controls
          class="h-9 flex-1"
        />
        <button
          class="rounded px-2 py-1 text-xs text-go4-muted transition hover:bg-red-50 hover:text-red-500 dark:hover:bg-red-900/20"
          @click="clearPreview"
        >
          Verwerfen
        </button>
      </div>

      <!-- ④ Name + Speichern in einer Zeile -->
      <div class="flex items-center gap-2">
        <input
          v-model="speakerName"
          type="text"
          placeholder="Name der Stimme"
          class="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
        >
        <button
          class="whitespace-nowrap rounded-lg bg-go4-primary px-5 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90 disabled:opacity-50"
          :disabled="uploading || !speakerName"
          @click="handleUpload"
        >
          {{ uploading ? 'Speichert...' : 'Speichern' }}
        </button>
      </div>
    </div>

    <!-- Conversion failed -->
    <p
      v-if="!previewUrl && !isRecording && recordingTime > 0 && !error"
      class="text-center text-xs text-amber-600"
    >
      Konvertierung fehlgeschlagen. Bitte erneut versuchen.
    </p>

    <!-- Error / Success -->
    <p
      v-if="error"
      class="text-center text-xs text-red-600"
    >
      {{ error }}
    </p>
    <p
      v-if="success"
      class="text-center text-xs text-green-600"
    >
      {{ success }}
    </p>

    <!-- ⑤ Gespeicherte Stimmen -->
    <div v-if="store.speakerVoices.length">
      <h3 class="mb-2 text-sm font-medium text-go4-secondary dark:text-gray-100">
        Gespeicherte Stimmen ({{ store.speakerVoices.length }})
      </h3>
      <div class="space-y-1.5">
        <div
          v-for="voice in store.speakerVoices"
          :key="voice.name"
          class="flex items-center gap-3 rounded-lg bg-go4-surface px-3 py-2 dark:bg-gray-900"
        >
          <span class="min-w-0 flex-1 truncate text-sm font-medium text-go4-secondary dark:text-gray-100">
            {{ voice.name }}
          </span>
          <span class="shrink-0 text-xs text-go4-muted dark:text-gray-500">
            {{ Math.round(voice.size_bytes / 1024) }} KB
          </span>
          <audio
            :src="voice.url"
            controls
            class="h-7 shrink-0"
          />
          <button
            class="shrink-0 text-xs text-red-500 transition hover:text-red-700"
            @click="handleDelete(voice.name)"
          >
            Loeschen
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
