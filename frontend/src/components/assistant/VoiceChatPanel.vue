<script setup>
import { nextTick, onMounted, ref, watch } from 'vue'
import { useVoiceChatStore } from '@/stores/voiceChat'
import { useAudioRecording } from '@/composables/useAudioRecording'
import { useAudioPlayback } from '@/composables/useAudioPlayback'

const store = useVoiceChatStore()
const { isRecording, error: micError, startRecording, stopRecording } = useAudioRecording()
const { isPlaying, playBase64Audio, stop: stopAudio } = useAudioPlayback()

const inputText = ref('')
const messagesContainer = ref(null)
const showTurnDetails = ref(false)

// Auto-scroll on new messages
watch(
  () => store.messages.length,
  async () => {
    await nextTick()
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  },
)

onMounted(async () => {
  if (store.conversationId) {
    await store.refreshReviewState()
  }
})

async function handleSend() {
  const text = inputText.value.trim()
  if (!text || store.loading) return
  inputText.value = ''
  const result = await store.sendText(text)
  if (result?.audio_base64 && store.ttsEnabled) {
    await playBase64Audio(result.audio_base64)
  }
}

async function handleMicToggle() {
  if (isRecording.value) {
    const blob = await stopRecording()
    if (blob && blob.size > 0) {
      const result = await store.sendAudio(blob)
      if (result?.audio_base64 && store.ttsEnabled) {
        await playBase64Audio(result.audio_base64)
      }
    }
  } else {
    await startRecording()
  }
}

function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

function formatTime(date) {
  if (!date) return ''
  return new Date(date).toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })
}

function formatDateTime(date) {
  if (!date) return ''
  return new Date(date).toLocaleString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function turnBadge(turn) {
  if (turn.turn_type === 'tool') return 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300'
  if (turn.role === 'assistant') return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300'
  return 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
}

function turnLabel(turn) {
  if (turn.turn_type === 'tool') return turn.tool_name || 'Tool'
  return turn.role === 'assistant' ? 'Assistant' : 'User'
}
</script>

<template>
  <div class="flex h-[600px] flex-col rounded-lg bg-white shadow-sm dark:bg-gray-800">
    <div
      v-if="store.error"
      class="border-b border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/40 dark:bg-red-950/20 dark:text-red-300"
    >
      {{ store.error }}
    </div>

    <!-- Context Bar -->
    <div
      v-if="store.currentContext?.current_email"
      class="flex items-center gap-2 border-b border-gray-200 px-4 py-2 dark:border-gray-700"
    >
      <span class="text-xs font-medium text-go4-muted dark:text-gray-400">Aktuelle Email:</span>
      <span class="truncate text-xs text-go4-secondary dark:text-gray-200">
        {{ store.currentContext.current_email.subject }}
      </span>
      <span class="text-xs text-go4-muted dark:text-gray-400">
        von {{ store.currentContext.current_email.sender }}
      </span>
      <span
        v-if="store.currentContext.email_count"
        class="ml-auto text-xs text-go4-muted dark:text-gray-500"
      >
        {{ store.currentContext.current_index }}/{{ store.currentContext.email_count }}
      </span>
    </div>

    <!-- Debug/Pipeline panels hidden from voice chat — available via Pipeline section toggle -->
    <div
      v-if="false"
      class="border-b border-amber-200 bg-amber-50 px-4 py-3 dark:border-amber-900/40 dark:bg-amber-950/20"
    >
      <div
        v-if="store.currentContext?.cleanup_preview_summary"
        class="mb-3 rounded-lg border border-sky-200 bg-white/70 p-3 dark:border-sky-900/50 dark:bg-gray-900/30"
      >
        <p class="text-xs font-semibold uppercase tracking-wide text-sky-700 dark:text-sky-400">
          Cleanup-Vorschau
        </p>
        <p class="mt-1 whitespace-pre-wrap text-sm text-go4-secondary dark:text-gray-100">
          {{ store.currentContext.cleanup_preview_summary }}
        </p>
      </div>

      <div
        v-if="store.currentPendingIntent"
        class="rounded-lg border border-amber-200 bg-white/70 p-3 dark:border-amber-900/50 dark:bg-gray-900/30"
      >
        <div class="flex items-start justify-between gap-3">
          <div>
            <p class="text-xs font-semibold uppercase tracking-wide text-amber-700 dark:text-amber-400">
              Ausstehende Aktion
            </p>
            <p class="mt-1 text-sm font-medium text-go4-secondary dark:text-gray-100">
              {{ store.currentPendingIntent.intent_type }}
            </p>
            <p class="mt-1 text-xs text-go4-muted dark:text-gray-400">
              {{ store.currentPendingIntent.target_ref_json?.subject || store.currentPendingIntent.target_ref_json?.to || 'Keine Zieldetails' }}
            </p>
            <p
              v-if="store.currentPendingIntent.payload_json?.folder"
              class="mt-1 text-xs text-go4-muted dark:text-gray-400"
            >
              Ziel: {{ store.currentPendingIntent.payload_json.folder }}
            </p>
          </div>
          <div class="flex gap-2">
            <button
              class="rounded-md border border-amber-300 px-3 py-1 text-xs font-medium text-amber-700 transition hover:bg-amber-100 dark:border-amber-800 dark:text-amber-300 dark:hover:bg-amber-900/30"
              :disabled="store.loading"
              @click="store.cancelCurrentIntent()"
            >
              Abbrechen
            </button>
            <button
              class="rounded-md bg-amber-600 px-3 py-1 text-xs font-medium text-white transition hover:bg-amber-700 disabled:opacity-50"
              :disabled="store.loading"
              @click="store.confirmCurrentIntent()"
            >
              Jetzt ausfuehren
            </button>
          </div>
        </div>
      </div>

      <div
        v-if="store.currentDraft"
        class="mt-3 rounded-lg border border-blue-200 bg-white/70 p-3 dark:border-blue-900/50 dark:bg-gray-900/30"
      >
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <p class="text-xs font-semibold uppercase tracking-wide text-blue-700 dark:text-blue-400">
              Aktueller Entwurf
            </p>
            <p class="mt-1 text-sm font-medium text-go4-secondary dark:text-gray-100">
              {{ store.currentDraft.subject || '(ohne Betreff)' }}
            </p>
            <p class="mt-1 text-xs text-go4-muted dark:text-gray-400">
              An: {{ store.currentDraft.to_recipients_json?.items?.join(', ') || 'unbekannt' }}
            </p>
            <input
              v-model="store.draftEditor.subject"
              type="text"
              class="mt-2 w-full rounded-md border border-blue-200 bg-white px-2 py-1 text-sm text-go4-secondary focus:border-blue-500 focus:outline-none dark:border-blue-900/60 dark:bg-gray-900/50 dark:text-gray-100"
              placeholder="Betreff"
            >
            <textarea
              v-model="store.draftEditor.body_text"
              rows="4"
              class="mt-2 w-full rounded-md border border-blue-200 bg-white px-2 py-2 text-sm text-go4-secondary focus:border-blue-500 focus:outline-none dark:border-blue-900/60 dark:bg-gray-900/50 dark:text-gray-100"
              placeholder="Entwurf bearbeiten..."
            />
          </div>
          <div class="flex gap-2">
            <button
              class="rounded-md border border-blue-300 px-3 py-1 text-xs font-medium text-blue-700 transition hover:bg-blue-100 dark:border-blue-800 dark:text-blue-300 dark:hover:bg-blue-900/30"
              :disabled="store.loading"
              @click="store.saveCurrentDraft()"
            >
              Speichern
            </button>
            <button
              class="rounded-md border border-blue-300 px-3 py-1 text-xs font-medium text-blue-700 transition hover:bg-blue-100 dark:border-blue-800 dark:text-blue-300 dark:hover:bg-blue-900/30"
              :disabled="store.loading"
              @click="store.discardCurrentDraft()"
            >
              Verwerfen
            </button>
            <button
              class="rounded-md bg-blue-600 px-3 py-1 text-xs font-medium text-white transition hover:bg-blue-700 disabled:opacity-50"
              :disabled="store.loading"
              @click="store.sendCurrentDraft()"
            >
              Senden
            </button>
          </div>
        </div>
      </div>

      <div
        v-if="store.undoLogs.length"
        class="mt-3 rounded-lg border border-emerald-200 bg-white/70 p-3 dark:border-emerald-900/50 dark:bg-gray-900/30"
      >
        <p class="text-xs font-semibold uppercase tracking-wide text-emerald-700 dark:text-emerald-400">
          Rueckgaengig
        </p>
        <div
          v-for="undoLog in store.undoLogs"
          :key="undoLog.id"
          class="mt-2 flex items-center justify-between gap-3 rounded-md border border-emerald-100 px-2 py-2 dark:border-emerald-900/30"
        >
          <div class="min-w-0">
            <p class="truncate text-sm font-medium text-go4-secondary dark:text-gray-100">
              {{ undoLog.action_type }}
            </p>
            <p class="truncate text-xs text-go4-muted dark:text-gray-400">
              {{ undoLog.target_ref_json?.subject || undoLog.target_ref_json?.email_id || undoLog.target_ref_json?.draft_id || 'Kein Detail' }}
            </p>
          </div>
          <button
            class="rounded-md bg-emerald-600 px-3 py-1 text-xs font-medium text-white transition hover:bg-emerald-700 disabled:opacity-50"
            :disabled="store.loading"
            @click="store.undoLastAction(undoLog.id)"
          >
            Undo
          </button>
        </div>
      </div>
    </div>

    <div
      v-if="false"
      class="border-b border-gray-200 bg-gray-50 px-4 py-3 dark:border-gray-700 dark:bg-gray-900/40"
    >
      <div class="flex items-center justify-between gap-3">
        <div>
          <p class="text-xs font-semibold uppercase tracking-wide text-go4-muted dark:text-gray-400">
            Session-Kontext
          </p>
          <p class="mt-1 text-sm text-go4-secondary dark:text-gray-100">
            {{ store.conversationTurns.length }} persistierte Turns
            <span v-if="store.conversationId"> in Session #{{ store.conversationId }}</span>
          </p>
        </div>
        <button
          class="text-xs font-medium text-go4-primary transition hover:underline"
          @click="showTurnDetails = !showTurnDetails"
        >
          {{ showTurnDetails ? 'Details ausblenden' : 'Details zeigen' }}
        </button>
      </div>

      <div
        v-if="showTurnDetails"
        class="mt-3 max-h-40 space-y-2 overflow-y-auto"
      >
        <div
          v-for="turn in store.conversationTurns.slice(0, 12)"
          :key="turn.id"
          class="rounded-lg border border-gray-200 bg-white px-3 py-2 dark:border-gray-700 dark:bg-gray-800"
        >
          <div class="flex items-center justify-between gap-3">
            <div class="flex items-center gap-2">
              <span
                class="rounded-full px-2 py-0.5 text-[11px] font-semibold"
                :class="turnBadge(turn)"
              >
                {{ turnLabel(turn) }}
              </span>
              <span class="text-[11px] text-go4-muted dark:text-gray-500">
                {{ formatDateTime(turn.created_at) }}
              </span>
            </div>
            <span
              v-if="turn.latency_ms"
              class="text-[11px] text-go4-muted dark:text-gray-500"
            >
              {{ turn.latency_ms }} ms
            </span>
          </div>
          <p
            v-if="turn.content_text"
            class="mt-2 whitespace-pre-wrap text-xs text-go4-secondary dark:text-gray-200"
          >
            {{ turn.content_text }}
          </p>
          <p
            v-else-if="turn.tool_result_text"
            class="mt-2 whitespace-pre-wrap text-xs text-go4-secondary dark:text-gray-200"
          >
            {{ turn.tool_result_text }}
          </p>
        </div>
      </div>
    </div>

    <!-- Messages -->
    <div
      ref="messagesContainer"
      class="flex-1 space-y-3 overflow-y-auto p-4"
    >
      <div
        v-if="!store.messages.length"
        class="flex h-full items-center justify-center"
      >
        <div class="text-center">
          <p class="text-lg font-medium text-go4-secondary dark:text-gray-200">
            Sprachassistent
          </p>
          <p class="mt-1 text-sm text-go4-muted dark:text-gray-400">
            Frag mich nach deinen Emails — z.B. "Lies mir die 5 neuesten Emails vor"
          </p>
        </div>
      </div>

      <div
        v-for="(msg, i) in store.messages"
        :key="i"
        class="flex"
        :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
      >
        <div
          class="max-w-[80%] rounded-lg px-3 py-2"
          :class="[
            msg.role === 'user'
              ? 'bg-go4-primary text-white'
              : msg.isError
                ? 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400'
                : 'bg-go4-surface text-go4-secondary dark:bg-gray-700 dark:text-gray-200',
          ]"
        >
          <p class="whitespace-pre-wrap text-sm">
            {{ msg.content }}
          </p>
          <span
            class="mt-1 block text-right text-[10px]"
            :class="msg.role === 'user' ? 'text-white/60' : 'text-go4-muted dark:text-gray-500'"
          >
            {{ formatTime(msg.time) }}
          </span>
        </div>
      </div>

      <!-- Loading indicator -->
      <div
        v-if="store.loading"
        class="flex justify-start"
      >
        <div class="rounded-lg bg-go4-surface px-3 py-2 dark:bg-gray-700">
          <div class="flex items-center gap-1">
            <span
              class="h-2 w-2 animate-bounce rounded-full bg-go4-muted"
              style="animation-delay: 0ms"
            />
            <span
              class="h-2 w-2 animate-bounce rounded-full bg-go4-muted"
              style="animation-delay: 150ms"
            />
            <span
              class="h-2 w-2 animate-bounce rounded-full bg-go4-muted"
              style="animation-delay: 300ms"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Input Bar -->
    <div class="border-t border-gray-200 px-4 py-3 dark:border-gray-700">
      <!-- Mic error -->
      <p
        v-if="micError"
        class="mb-2 text-xs text-red-600"
      >
        {{ micError }}
      </p>

      <div class="flex items-center gap-2">
        <!-- Mic button -->
        <button
          class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full transition"
          :class="
            isRecording
              ? 'bg-red-500 text-white animate-pulse'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
          "
          :title="isRecording ? 'Aufnahme stoppen' : 'Sprachnachricht'"
          @click="handleMicToggle"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-5 w-5"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fill-rule="evenodd"
              d="M7 4a3 3 0 016 0v4a3 3 0 11-6 0V4zm4 10.93A7.001 7.001 0 0017 8a1 1 0 10-2 0A5 5 0 015 8a1 1 0 00-2 0 7.001 7.001 0 006 6.93V17H6a1 1 0 100 2h8a1 1 0 100-2h-3v-2.07z"
              clip-rule="evenodd"
            />
          </svg>
        </button>

        <!-- Text input -->
        <input
          v-model="inputText"
          type="text"
          placeholder="Nachricht eingeben..."
          class="flex-1 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 placeholder-gray-400 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:placeholder-gray-500"
          :disabled="store.loading || isRecording"
          @keydown="handleKeydown"
        >

        <!-- Send button -->
        <button
          class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-go4-primary text-white transition hover:bg-go4-primary/90 disabled:opacity-50"
          :disabled="(!inputText.trim() && !isRecording) || store.loading"
          @click="handleSend"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-5 w-5"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
          </svg>
        </button>

        <!-- TTS toggle -->
        <button
          class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full transition"
          :class="
            store.ttsEnabled
              ? 'bg-go4-primary/10 text-go4-primary'
              : 'bg-gray-100 text-gray-400 dark:bg-gray-700 dark:text-gray-500'
          "
          title="Sprachausgabe ein/aus"
          @click="store.ttsEnabled = !store.ttsEnabled"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-5 w-5"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              v-if="store.ttsEnabled"
              fill-rule="evenodd"
              d="M9.383 3.076A1 1 0 0110 4v12a1 1 0 01-1.707.707L4.586 13H2a1 1 0 01-1-1V8a1 1 0 011-1h2.586l3.707-3.707a1 1 0 011.09-.217zM14.657 2.929a1 1 0 011.414 0A9.972 9.972 0 0119 10a9.972 9.972 0 01-2.929 7.071 1 1 0 01-1.414-1.414A7.971 7.971 0 0017 10c0-2.21-.894-4.208-2.343-5.657a1 1 0 010-1.414zm-2.829 2.828a1 1 0 011.415 0A5.983 5.983 0 0115 10a5.984 5.984 0 01-1.757 4.243 1 1 0 01-1.415-1.415A3.984 3.984 0 0013 10a3.983 3.983 0 00-1.172-2.828 1 1 0 010-1.415z"
              clip-rule="evenodd"
            />
            <path
              v-else
              fill-rule="evenodd"
              d="M9.383 3.076A1 1 0 0110 4v12a1 1 0 01-1.707.707L4.586 13H2a1 1 0 01-1-1V8a1 1 0 011-1h2.586l3.707-3.707a1 1 0 011.09-.217zM12.293 7.293a1 1 0 011.414 0L15 8.586l1.293-1.293a1 1 0 111.414 1.414L16.414 10l1.293 1.293a1 1 0 01-1.414 1.414L15 11.414l-1.293 1.293a1 1 0 01-1.414-1.414L13.586 10l-1.293-1.293a1 1 0 010-1.414z"
              clip-rule="evenodd"
            />
          </svg>
        </button>

        <!-- Stop audio -->
        <button
          v-if="isPlaying"
          class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-red-100 text-red-600 transition hover:bg-red-200"
          title="Audio stoppen"
          @click="stopAudio"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-5 w-5"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fill-rule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8 7a1 1 0 00-1 1v4a1 1 0 001 1h4a1 1 0 001-1V8a1 1 0 00-1-1H8z"
              clip-rule="evenodd"
            />
          </svg>
        </button>
      </div>

      <!-- Controls row -->
      <div class="mt-2 flex items-center justify-between">
        <button
          class="text-xs text-go4-muted transition hover:text-go4-secondary dark:text-gray-500 dark:hover:text-gray-300"
          @click="store.clearChat()"
        >
          Chat leeren
        </button>
        <span
          v-if="store.conversationId"
          class="text-[10px] text-go4-muted dark:text-gray-600"
        >
          Session #{{ store.conversationId }}
        </span>
      </div>
    </div>
  </div>
</template>
