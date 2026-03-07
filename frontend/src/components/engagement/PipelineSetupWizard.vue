<script setup>
import { ref, nextTick, computed } from 'vue'
import { useEngagementStore } from '@/stores/engagement'

const props = defineProps({
  visible: { type: Boolean, default: false }
})

const emit = defineEmits(['close', 'complete'])

const store = useEngagementStore()

// Wizard steps
const steps = ['chat', 'prerequisites', 'review']
const currentStep = ref('chat')
const stepIndex = computed(() => steps.indexOf(currentStep.value))

// Chat state
const messages = ref([])
const userInput = ref('')
const loading = ref(false)
const error = ref(null)
const conversationHistory = ref([])

// Pipeline config from chat
const pipelineConfig = ref(null)
const prerequisites = ref(null)
const creating = ref(false)

// Refs
const messagesContainer = ref(null)
const inputRef = ref(null)

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// Start the wizard
async function start() {
  loading.value = true
  error.value = null
  messages.value = []
  pipelineConfig.value = null
  prerequisites.value = null
  currentStep.value = 'chat'
  conversationHistory.value = []

  try {
    const data = await store.sendSetupMessage(
      'Ich möchte eine neue Pipeline erstellen.',
      []
    )
    messages.value.push({
      role: 'assistant',
      content: data.message
    })
    conversationHistory.value.push(
      { role: 'user', content: 'Ich möchte eine neue Pipeline erstellen.' },
      { role: 'assistant', content: data.message }
    )
    scrollToBottom()
    nextTick(() => inputRef.value?.focus())
  } catch (err) {
    error.value = err.message || 'Fehler beim Starten des Assistenten'
  } finally {
    loading.value = false
  }
}

// Send chat message
async function sendMessage() {
  if (!userInput.value.trim() || loading.value) return

  const message = userInput.value.trim()
  userInput.value = ''

  messages.value.push({ role: 'user', content: message })
  conversationHistory.value.push({ role: 'user', content: message })
  scrollToBottom()

  loading.value = true
  error.value = null

  try {
    const data = await store.sendSetupMessage(message, conversationHistory.value)

    messages.value.push({ role: 'assistant', content: data.message })
    conversationHistory.value.push({ role: 'assistant', content: data.message })
    scrollToBottom()

    // Check if brain returned pipeline config
    if (data.pipeline_config) {
      pipelineConfig.value = data.pipeline_config
      // Move to prerequisites check
      await checkPrerequisites()
    }
  } catch (err) {
    error.value = err.message || 'Fehler beim Senden'
  } finally {
    loading.value = false
    nextTick(() => inputRef.value?.focus())
  }
}

// Check prerequisites for selected channels
async function checkPrerequisites() {
  if (!pipelineConfig.value?.channels?.length) return

  currentStep.value = 'prerequisites'
  loading.value = true
  error.value = null

  try {
    const data = await store.checkChannelPrerequisites(pipelineConfig.value.channels)
    prerequisites.value = data
  } catch (err) {
    error.value = err.message || 'Fehler bei Voraussetzungsprüfung'
  } finally {
    loading.value = false
  }
}

// Move to review step
function goToReview() {
  currentStep.value = 'review'
}

// Create pipeline from setup
async function createPipeline() {
  creating.value = true
  error.value = null

  try {
    const data = await store.createFromSetup({
      pipeline_config: pipelineConfig.value,
      check_prerequisites: false,
      generate_playbook: true,
      generate_module_prompts: true
    })

    emit('complete', data)
  } catch (err) {
    error.value = err.response?.data?.detail || err.message
  } finally {
    creating.value = false
  }
}

// Fill form instead of auto-creating
function fillFormAndClose() {
  emit('complete', { pipeline_config: pipelineConfig.value, fill_form: true })
}

function close() {
  emit('close')
}

// Computed helpers
const hasBlockers = computed(() => {
  if (!prerequisites.value?.checks) return false
  return prerequisites.value.checks.some((c) => c.status === 'blocker')
})

const prerequisitesByStatus = computed(() => {
  if (!prerequisites.value?.checks) return { ready: [], warning: [], blocker: [] }
  const checks = prerequisites.value.checks
  return {
    ready: checks.filter((c) => c.status === 'ready'),
    warning: checks.filter((c) => c.status === 'warning'),
    blocker: checks.filter((c) => c.status === 'blocker')
  }
})

// Watch visibility
import { watch } from 'vue'
watch(
  () => props.visible,
  (visible) => {
    if (visible) start()
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
      class="flex h-[650px] w-full max-w-2xl flex-col rounded-lg bg-white shadow-xl dark:bg-gray-800"
    >
      <!-- Header with Steps -->
      <div
        class="border-b border-gray-200 px-4 py-3 dark:border-gray-700"
      >
        <div class="flex items-center justify-between">
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
                  d="M13 10V3L4 14h7v7l9-11h-7z"
                />
              </svg>
            </div>
            <div>
              <h3 class="font-medium text-go4-secondary dark:text-white">
                Pipeline Setup-Assistent
              </h3>
              <p class="text-xs text-go4-muted">
                KI-gesteuertes Pipeline-Setup
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

        <!-- Step indicator -->
        <div class="mt-3 flex items-center gap-2">
          <div
            v-for="(step, idx) in steps"
            :key="step"
            class="flex items-center gap-2"
          >
            <div
              class="flex h-6 w-6 items-center justify-center rounded-full text-xs font-medium"
              :class="
                idx <= stepIndex
                  ? 'bg-go4-primary text-white'
                  : 'bg-gray-200 text-gray-500 dark:bg-gray-600 dark:text-gray-400'
              "
            >
              {{ idx + 1 }}
            </div>
            <span
              class="text-xs"
              :class="
                idx <= stepIndex
                  ? 'text-go4-primary font-medium'
                  : 'text-gray-400'
              "
            >
              {{ { chat: 'Dialog', prerequisites: 'Prüfung', review: 'Erstellen' }[step] }}
            </span>
            <svg
              v-if="idx < steps.length - 1"
              class="h-4 w-4 text-gray-300"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M9 5l7 7-7 7"
              />
            </svg>
          </div>
        </div>
      </div>

      <!-- Content area -->
      <div class="flex-1 overflow-auto p-4">
        <!-- STEP 1: Chat -->
        <div
          v-if="currentStep === 'chat'"
          class="flex h-full flex-col"
        >
          <div
            ref="messagesContainer"
            class="flex-1 space-y-4 overflow-y-auto"
          >
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
                <p class="whitespace-pre-wrap text-sm">
                  {{ msg.content }}
                </p>
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
          </div>
        </div>

        <!-- STEP 2: Prerequisites -->
        <div
          v-else-if="currentStep === 'prerequisites'"
          class="space-y-4"
        >
          <h4 class="text-lg font-semibold text-gray-900 dark:text-white">
            Voraussetzungen
          </h4>
          <p class="text-sm text-gray-500">
            Prüfung der Kanal-Konfiguration für diese Pipeline.
          </p>

          <!-- Loading -->
          <div
            v-if="loading"
            class="flex items-center justify-center py-8"
          >
            <svg
              class="h-8 w-8 animate-spin text-go4-primary"
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
          </div>

          <!-- Results -->
          <div
            v-else-if="prerequisites"
            class="space-y-3"
          >
            <!-- Ready -->
            <div
              v-for="check in prerequisitesByStatus.ready"
              :key="check.component"
              class="flex items-start gap-3 rounded-lg bg-green-50 p-3 dark:bg-green-900/20"
            >
              <svg
                class="mt-0.5 h-5 w-5 flex-shrink-0 text-green-500"
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
              <div>
                <p class="font-medium text-green-700 dark:text-green-400">
                  {{ check.channel }}: {{ check.component }}
                </p>
                <p class="text-sm text-green-600 dark:text-green-300">
                  {{ check.message }}
                </p>
              </div>
            </div>

            <!-- Warnings -->
            <div
              v-for="check in prerequisitesByStatus.warning"
              :key="check.component"
              class="flex items-start gap-3 rounded-lg bg-yellow-50 p-3 dark:bg-yellow-900/20"
            >
              <svg
                class="mt-0.5 h-5 w-5 flex-shrink-0 text-yellow-500"
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
              <div>
                <p class="font-medium text-yellow-700 dark:text-yellow-400">
                  {{ check.channel }}: {{ check.component }}
                </p>
                <p class="text-sm text-yellow-600 dark:text-yellow-300">
                  {{ check.message }}
                </p>
              </div>
            </div>

            <!-- Blockers -->
            <div
              v-for="check in prerequisitesByStatus.blocker"
              :key="check.component"
              class="flex items-start gap-3 rounded-lg bg-red-50 p-3 dark:bg-red-900/20"
            >
              <svg
                class="mt-0.5 h-5 w-5 flex-shrink-0 text-red-500"
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
              <div>
                <p class="font-medium text-red-700 dark:text-red-400">
                  {{ check.channel }}: {{ check.component }}
                </p>
                <p class="text-sm text-red-600 dark:text-red-300">
                  {{ check.message }}
                </p>
              </div>
            </div>
          </div>
        </div>

        <!-- STEP 3: Review -->
        <div
          v-else-if="currentStep === 'review'"
          class="space-y-4"
        >
          <h4 class="text-lg font-semibold text-gray-900 dark:text-white">
            Pipeline-Konfiguration
          </h4>

          <div
            v-if="pipelineConfig"
            class="space-y-3"
          >
            <div class="rounded-lg bg-gray-50 p-4 dark:bg-gray-700">
              <dl class="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <dt class="font-medium text-gray-500 dark:text-gray-400">
                    Name
                  </dt>
                  <dd class="text-gray-900 dark:text-white">
                    {{ pipelineConfig.name || '—' }}
                  </dd>
                </div>
                <div>
                  <dt class="font-medium text-gray-500 dark:text-gray-400">
                    Produkt
                  </dt>
                  <dd class="text-gray-900 dark:text-white">
                    {{ pipelineConfig.product_name || '—' }}
                  </dd>
                </div>
                <div class="col-span-2">
                  <dt class="font-medium text-gray-500 dark:text-gray-400">
                    Zielgruppe
                  </dt>
                  <dd class="text-gray-900 dark:text-white">
                    {{ pipelineConfig.target_audience || '—' }}
                  </dd>
                </div>
                <div>
                  <dt class="font-medium text-gray-500 dark:text-gray-400">
                    Kanäle
                  </dt>
                  <dd class="flex flex-wrap gap-1">
                    <span
                      v-for="ch in pipelineConfig.channels"
                      :key="ch"
                      class="rounded-full bg-go4-primary/10 px-2 py-0.5 text-xs font-medium text-go4-primary"
                    >
                      {{ ch }}
                    </span>
                  </dd>
                </div>
                <div>
                  <dt class="font-medium text-gray-500 dark:text-gray-400">
                    Ziel
                  </dt>
                  <dd class="text-gray-900 dark:text-white">
                    {{ pipelineConfig.goal || '—' }}
                  </dd>
                </div>
                <div>
                  <dt class="font-medium text-gray-500 dark:text-gray-400">
                    Tonalität
                  </dt>
                  <dd class="text-gray-900 dark:text-white">
                    {{ pipelineConfig.tone_of_voice || '—' }}
                  </dd>
                </div>
              </dl>
            </div>

            <div class="rounded-lg bg-blue-50 p-3 text-sm text-blue-700 dark:bg-blue-900/20 dark:text-blue-300">
              <p class="font-medium">
                Bei Erstellung wird das Brain:
              </p>
              <ul class="mt-1 list-inside list-disc">
                <li>Ein Playbook für die Pipeline generieren</li>
                <li>Modul-Prompts für jeden Kanal erstellen</li>
              </ul>
            </div>
          </div>

          <!-- Creating indicator -->
          <div
            v-if="creating"
            class="flex items-center justify-center gap-3 py-4"
          >
            <svg
              class="h-6 w-6 animate-spin text-go4-primary"
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
            <span class="text-go4-muted">Pipeline wird erstellt, Playbook und Prompts generiert...</span>
          </div>
        </div>

        <!-- Error -->
        <div
          v-if="error"
          class="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-300"
        >
          {{ error }}
        </div>
      </div>

      <!-- Footer -->
      <div class="border-t border-gray-200 p-4 dark:border-gray-700">
        <!-- Chat input -->
        <form
          v-if="currentStep === 'chat'"
          class="flex gap-2"
          @submit.prevent="sendMessage"
        >
          <input
            ref="inputRef"
            v-model="userInput"
            type="text"
            placeholder="Beschreibe dein Produkt, Zielgruppe, Kanäle..."
            class="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-go4-primary focus:outline-none dark:border-gray-600 dark:bg-gray-700"
            :disabled="loading"
          >
          <button
            type="submit"
            class="rounded-lg bg-go4-primary px-4 py-2 text-white hover:bg-go4-primary-dark disabled:opacity-50"
            :disabled="loading || !userInput.trim()"
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

        <!-- Prerequisites actions -->
        <div
          v-else-if="currentStep === 'prerequisites'"
          class="flex justify-between"
        >
          <button
            class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300"
            @click="currentStep = 'chat'"
          >
            Zurück
          </button>
          <div class="flex gap-2">
            <button
              class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300"
              @click="fillFormAndClose"
            >
              Manuell bearbeiten
            </button>
            <button
              class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark disabled:opacity-50"
              :disabled="hasBlockers"
              @click="goToReview"
            >
              Weiter
            </button>
          </div>
        </div>

        <!-- Review actions -->
        <div
          v-else-if="currentStep === 'review'"
          class="flex justify-between"
        >
          <button
            class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300"
            @click="currentStep = 'prerequisites'"
          >
            Zurück
          </button>
          <div class="flex gap-2">
            <button
              class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300"
              @click="fillFormAndClose"
            >
              Manuell bearbeiten
            </button>
            <button
              class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark disabled:opacity-50"
              :disabled="creating"
              @click="createPipeline"
            >
              Pipeline erstellen
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
