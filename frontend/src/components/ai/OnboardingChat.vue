<script setup>
import { ref, nextTick, onMounted, computed } from 'vue'
import { marked } from 'marked'
import { startOnboarding, sendOnboardingMessage } from '@/api/ai'

// Configure marked for safe rendering
marked.setOptions({
  breaks: true,
  gfm: true
})

// Render markdown for assistant messages
function renderMarkdown(content) {
  if (!content) return ''
  return marked(content)
}

const props = defineProps({
  module: { type: String, required: true },
  visible: { type: Boolean, default: false }
})

const emit = defineEmits(['close', 'complete'])

// Chat state
const messages = ref([])
const userInput = ref('')
const loading = ref(false)
const conversationId = ref(null)
const isComplete = ref(false)
const error = ref(null)
const generatedPrompts = ref([])

// Refs
const messagesContainer = ref(null)
const inputRef = ref(null)

// Scroll to bottom
function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// Start the onboarding
async function start() {
  loading.value = true
  error.value = null
  messages.value = []
  isComplete.value = false

  try {
    const { data } = await startOnboarding(props.module)
    conversationId.value = data.conversation_id
    messages.value.push({
      role: 'assistant',
      content: data.first_message
    })
    scrollToBottom()
    nextTick(() => inputRef.value?.focus())
  } catch (err) {
    error.value = err.message || 'Fehler beim Starten des Onboardings'
  } finally {
    loading.value = false
  }
}

// Send a message
async function sendMessage() {
  if (!userInput.value.trim() || loading.value || !conversationId.value) return

  const message = userInput.value.trim()
  userInput.value = ''

  messages.value.push({
    role: 'user',
    content: message
  })
  scrollToBottom()

  loading.value = true
  error.value = null

  try {
    const { data } = await sendOnboardingMessage(props.module, conversationId.value, message)
    messages.value.push({
      role: 'assistant',
      content: data.message
    })
    scrollToBottom()

    if (data.is_complete) {
      isComplete.value = true
      generatedPrompts.value = data.prompts_generated || []
      emit('complete', {
        extracted_data: data.extracted_data,
        prompts_generated: data.prompts_generated || []
      })
    }
  } catch (err) {
    error.value = err.message || 'Fehler beim Senden der Nachricht'
  } finally {
    loading.value = false
    nextTick(() => inputRef.value?.focus())
  }
}

// Close the chat
function close() {
  emit('close')
}

// Auto-start when visible
onMounted(() => {
  if (props.visible && !conversationId.value) {
    start()
  }
})

// Watch for visibility changes
import { watch } from 'vue'
watch(
  () => props.visible,
  (visible) => {
    if (visible && !conversationId.value) {
      start()
    }
  }
)
</script>

<template>
  <div
    v-if="visible"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
    @click.self="close"
  >
    <div
      class="flex h-[600px] w-full max-w-2xl flex-col rounded-lg bg-white shadow-xl dark:bg-gray-800"
    >
      <!-- Header -->
      <div
        class="flex items-center justify-between border-b border-gray-200 px-4 py-3 dark:border-gray-700"
      >
        <div class="flex items-center gap-2">
          <div
            class="flex h-8 w-8 items-center justify-center rounded-full bg-go4-primary text-white"
          >
            <svg
              class="h-5 w-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
              />
            </svg>
          </div>
          <div>
            <h3 class="font-medium text-go4-secondary dark:text-white">
              Setup-Assistent
            </h3>
            <p class="text-xs text-go4-muted">
              {{ module }} konfigurieren
            </p>
          </div>
        </div>
        <button
          class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          @click="close"
        >
          <svg
            class="h-5 w-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>

      <!-- Messages -->
      <div
        ref="messagesContainer"
        class="flex-1 overflow-y-auto p-4 space-y-4"
      >
        <!-- Loading initial -->
        <div
          v-if="loading && messages.length === 0"
          class="flex justify-center py-8"
        >
          <div class="flex items-center gap-2 text-go4-muted">
            <svg
              class="h-5 w-5 animate-spin"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                class="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                stroke-width="4"
              />
              <path
                class="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            <span>Starte Setup-Assistent...</span>
          </div>
        </div>

        <!-- Error -->
        <div
          v-if="error"
          class="rounded-lg bg-red-50 p-4 dark:bg-red-900/20"
        >
          <div class="flex items-start gap-3">
            <svg
              class="h-5 w-5 flex-shrink-0 text-red-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
            <div class="flex-1">
              <p class="font-medium text-red-700 dark:text-red-400">
                Fehler
              </p>
              <p class="mt-1 text-sm text-red-600 dark:text-red-300">
                {{ error }}
              </p>
              <button
                class="mt-2 rounded bg-red-100 px-3 py-1 text-sm font-medium text-red-700 hover:bg-red-200 dark:bg-red-800/50 dark:text-red-300 dark:hover:bg-red-800"
                @click="start"
              >
                Neu versuchen
              </button>
            </div>
          </div>
        </div>

        <!-- Messages -->
        <div
          v-for="(msg, idx) in messages"
          :key="idx"
          :class="['flex', msg.role === 'user' ? 'justify-end' : 'justify-start']"
        >
          <div
            :class="[
              'max-w-[80%] rounded-lg px-4 py-2',
              msg.role === 'user'
                ? 'bg-go4-primary text-white'
                : 'bg-gray-100 text-go4-secondary dark:bg-gray-700 dark:text-white'
            ]"
          >
            <!-- User messages: plain text -->
            <p
              v-if="msg.role === 'user'"
              class="whitespace-pre-wrap"
            >
              {{ msg.content }}
            </p>
            <!-- Assistant messages: markdown -->
            <div
              v-else
              class="prose prose-sm dark:prose-invert max-w-none prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0"
              v-html="renderMarkdown(msg.content)"
            />
          </div>
        </div>

        <!-- Typing indicator -->
        <div
          v-if="loading && messages.length > 0"
          class="flex justify-start"
        >
          <div class="rounded-lg bg-gray-100 px-4 py-2 dark:bg-gray-700">
            <div class="flex gap-1">
              <span
                class="h-2 w-2 animate-bounce rounded-full bg-gray-400"
                style="animation-delay: 0ms"
              />
              <span
                class="h-2 w-2 animate-bounce rounded-full bg-gray-400"
                style="animation-delay: 150ms"
              />
              <span
                class="h-2 w-2 animate-bounce rounded-full bg-gray-400"
                style="animation-delay: 300ms"
              />
            </div>
          </div>
        </div>

        <!-- Completion message -->
        <div
          v-if="isComplete"
          class="rounded-lg bg-green-50 p-4 text-green-700 dark:bg-green-900/20 dark:text-green-400"
        >
          <div class="flex items-center gap-2">
            <svg
              class="h-5 w-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M5 13l4 4L19 7"
              />
            </svg>
            <span class="font-medium">Setup abgeschlossen!</span>
          </div>
          <p class="mt-1 text-sm">
            Die Konfiguration wurde gespeichert.
          </p>

          <!-- Generated Prompts -->
          <div
            v-if="generatedPrompts.length > 0"
            class="mt-3 border-t border-green-200 pt-3 dark:border-green-800"
          >
            <p class="text-sm font-medium">
              Generierte Prompts:
            </p>
            <ul class="mt-1 list-inside list-disc text-sm">
              <li
                v-for="slug in generatedPrompts"
                :key="slug"
              >
                {{ slug }}
              </li>
            </ul>
          </div>
        </div>
      </div>

      <!-- Input -->
      <div class="border-t border-gray-200 p-4 dark:border-gray-700">
        <form
          class="flex gap-2"
          @submit.prevent="sendMessage"
        >
          <input
            ref="inputRef"
            v-model="userInput"
            type="text"
            placeholder="Deine Antwort..."
            class="flex-1 rounded-lg border border-gray-300 px-4 py-2 focus:border-go4-primary focus:outline-none dark:border-gray-600 dark:bg-gray-700"
            :disabled="loading || isComplete"
          >
          <button
            type="submit"
            class="rounded-lg bg-go4-primary px-4 py-2 text-white hover:bg-go4-primary-dark disabled:opacity-50"
            :disabled="loading || isComplete || !userInput.trim()"
          >
            <svg
              class="h-5 w-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
              />
            </svg>
          </button>
        </form>

        <!-- Close button when complete -->
        <div
          v-if="isComplete"
          class="mt-3 text-center"
        >
          <button
            class="rounded-lg bg-go4-primary px-6 py-2 text-white hover:bg-go4-primary-dark"
            @click="close"
          >
            Fertig
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
