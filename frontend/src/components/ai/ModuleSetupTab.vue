<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import draggable from 'vuedraggable'
import {
  getModuleContext,
  getModulePrompts,
  getModuleParameters,
  createParameter,
  updateParameter,
  deleteParameter,
  reorderParameters,
  reorderPrompts,
  resetOnboarding,
  deletePrompt
} from '@/api/ai'
import ModuleParametersTable from './ModuleParametersTable.vue'
import OnboardingChat from './OnboardingChat.vue'
import PromptEditModal from './PromptEditModal.vue'

const props = defineProps({
  module: { type: String, required: true },
  moduleLabel: { type: String, default: '' }
})

const emit = defineEmits(['runPrompt'])

// State
const loading = ref(false)
const error = ref(null)
const context = ref(null)
const parameters = ref([])
const prompts = ref({ setup: [], productive: [] })
const showOnboarding = ref(false)

// Local copies for drag-and-drop
const localSetupPrompts = ref([])
const localProductivePrompts = ref([])

// Sync prompts with local copies
watch(
  () => prompts.value,
  (newPrompts) => {
    localSetupPrompts.value = [...(newPrompts.setup || [])]
    localProductivePrompts.value = [...(newPrompts.productive || [])]
  },
  { immediate: true, deep: true }
)

// Prompt Edit Modal State
const showPromptModal = ref(false)
const editingPrompt = ref(null)
const isDuplicating = ref(false)
const newPromptType = ref('productive')

// Computed
const onboardingCompleted = computed(() => context.value?.onboarding_completed || false)

// Load data
async function loadData() {
  loading.value = true
  error.value = null

  try {
    const [contextRes, paramsRes, promptsRes] = await Promise.all([
      getModuleContext(props.module),
      getModuleParameters(props.module),
      getModulePrompts(props.module)
    ])
    context.value = contextRes.data
    parameters.value = paramsRes.data
    prompts.value = promptsRes.data
  } catch (err) {
    error.value = err.message || 'Fehler beim Laden'
  } finally {
    loading.value = false
  }
}

// Parameter handlers
async function handleUpdateParameter(variable, data) {
  try {
    await updateParameter(props.module, variable, data)
    await loadData()
  } catch (err) {
    error.value = err.message || 'Fehler beim Speichern'
  }
}

async function handleDeleteParameter(variable) {
  try {
    await deleteParameter(props.module, variable)
    await loadData()
  } catch (err) {
    error.value = err.message || 'Fehler beim Löschen'
  }
}

async function handleAddParameter(data) {
  try {
    await createParameter(props.module, data)
    await loadData()
  } catch (err) {
    error.value = err.message || 'Fehler beim Erstellen'
  }
}

async function handleReorderParameters(order) {
  try {
    await reorderParameters(props.module, order)
    // No reload needed, local state is already updated
  } catch (err) {
    error.value = err.message || 'Fehler beim Sortieren'
    await loadData() // Reload to fix state
  }
}

// Prompt reorder handlers
async function onSetupPromptsReorder() {
  const order = localSetupPrompts.value.map((p) => p.id)
  try {
    await reorderPrompts(props.module, 'setup', order)
  } catch (err) {
    error.value = err.message || 'Fehler beim Sortieren'
    await loadData()
  }
}

async function onProductivePromptsReorder() {
  const order = localProductivePrompts.value.map((p) => p.id)
  try {
    await reorderPrompts(props.module, 'productive', order)
  } catch (err) {
    error.value = err.message || 'Fehler beim Sortieren'
    await loadData()
  }
}

// Reset onboarding
async function handleResetOnboarding() {
  if (!confirm('Onboarding wirklich zurücksetzen? Alle Parameter werden gelöscht.')) return

  try {
    await resetOnboarding(props.module)
    await loadData()
    showOnboarding.value = true
  } catch (err) {
    error.value = err.response?.data?.detail || 'Fehler beim Zurücksetzen'
  }
}

// Start onboarding
function startOnboardingDialog() {
  showOnboarding.value = true
}

// Onboarding complete
async function handleOnboardingComplete() {
  showOnboarding.value = false
  await loadData()
}

// Prompt Modal Functions
function openEditPrompt(prompt) {
  editingPrompt.value = prompt
  isDuplicating.value = false
  showPromptModal.value = true
}

function openDuplicatePrompt(prompt) {
  editingPrompt.value = prompt
  isDuplicating.value = true
  showPromptModal.value = true
}

function openCreatePrompt(type) {
  editingPrompt.value = null
  isDuplicating.value = false
  newPromptType.value = type
  showPromptModal.value = true
}

function closePromptModal() {
  showPromptModal.value = false
  editingPrompt.value = null
  isDuplicating.value = false
}

async function handlePromptSaved() {
  closePromptModal()
  await loadData()
}

async function handleDeletePrompt(prompt) {
  if (!confirm(`Prompt "${prompt.name}" wirklich löschen?`)) return

  try {
    await deletePrompt(props.module, prompt.id)
    await loadData()
  } catch (err) {
    error.value = err.response?.data?.detail || 'Fehler beim Löschen'
  }
}

// Check for first-time onboarding
onMounted(async () => {
  await loadData()

  // Auto-show onboarding if not completed and has onboarding prompt
  if (!onboardingCompleted.value && prompts.value.setup.some((p) => p.slug === 'onboarding')) {
    showOnboarding.value = true
  }
})
</script>

<template>
  <div class="space-y-6">
    <!-- Loading -->
    <div
      v-if="loading && !context"
      class="py-12 text-center text-go4-muted"
    >
      Laden...
    </div>

    <!-- Error -->
    <div
      v-else-if="error"
      class="rounded-lg bg-red-50 p-4 text-red-700 dark:bg-red-900/20"
    >
      {{ error }}
      <button
        class="ml-2 underline"
        @click="loadData"
      >
        Neu laden
      </button>
    </div>

    <!-- Content -->
    <template v-else>
      <!-- Onboarding Status -->
      <div
        class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
      >
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div
              :class="[
                'flex h-10 w-10 items-center justify-center rounded-full',
                onboardingCompleted
                  ? 'bg-green-100 text-green-600 dark:bg-green-900/30'
                  : 'bg-yellow-100 text-yellow-600 dark:bg-yellow-900/30'
              ]"
            >
              <svg
                v-if="onboardingCompleted"
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
              <svg
                v-else
                class="h-5 w-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <div>
              <h3 class="font-medium text-go4-secondary dark:text-white">
                Onboarding
              </h3>
              <p class="text-sm text-go4-muted">
                {{
                  onboardingCompleted
                    ? 'Konfiguration abgeschlossen'
                    : 'Starte den Setup-Assistenten um das Modul zu konfigurieren'
                }}
              </p>
            </div>
          </div>
          <div class="flex gap-2">
            <button
              v-if="onboardingCompleted"
              class="rounded-lg border border-gray-300 px-4 py-2 text-sm hover:bg-gray-100 dark:border-gray-600 dark:hover:bg-gray-700"
              @click="handleResetOnboarding"
            >
              Zurücksetzen
            </button>
            <button
              class="rounded-lg bg-go4-primary px-4 py-2 text-sm text-white hover:bg-go4-primary-dark"
              @click="startOnboardingDialog"
            >
              {{ onboardingCompleted ? 'Erneut starten' : 'Setup starten' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Parameters Section -->
      <ModuleParametersTable
        :parameters="parameters"
        :loading="loading"
        @update="handleUpdateParameter"
        @delete="handleDeleteParameter"
        @add="handleAddParameter"
        @reorder="handleReorderParameters"
      />

      <!-- Prompts Section - Single Column Layout -->
      <div class="rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
        <div class="border-b border-gray-200 px-4 py-3 dark:border-gray-700">
          <h3 class="text-lg font-medium text-go4-secondary dark:text-white">
            Prompts
          </h3>
        </div>

        <div class="divide-y divide-gray-200 dark:divide-gray-700">
          <!-- Setup Prompts Section -->
          <div class="p-4">
            <div class="mb-3 flex items-center justify-between">
              <h4 class="flex items-center gap-2 text-sm font-semibold text-go4-secondary dark:text-white">
                <svg
                  class="h-4 w-4 text-blue-500"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                  />
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                  />
                </svg>
                Setup Prompts
                <span class="rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                  {{ prompts.setup.length }}
                </span>
              </h4>
              <button
                class="rounded px-2 py-1 text-xs text-go4-primary hover:bg-go4-primary/10"
                @click="openCreatePrompt('setup')"
              >
                + Neu
              </button>
            </div>
            <p class="mb-3 text-xs text-go4-muted">
              Prompts für Onboarding und Konfiguration
            </p>
            <div
              v-if="localSetupPrompts.length === 0"
              class="text-sm text-go4-muted italic"
            >
              Keine Setup-Prompts definiert
            </div>
            <draggable
              v-else
              :list="localSetupPrompts"
              item-key="id"
              handle=".drag-handle"
              ghost-class="bg-go4-primary/10"
              class="space-y-1"
              @end="onSetupPromptsReorder"
            >
              <template #item="{ element: prompt }">
                <div
                  class="group flex items-center justify-between rounded-lg border border-gray-100 bg-gray-50 px-3 py-2 hover:border-go4-primary/30 hover:bg-go4-primary/5 cursor-pointer transition dark:border-gray-600 dark:bg-gray-700/50"
                  @click="openEditPrompt(prompt)"
                >
                  <div class="flex items-center gap-2 min-w-0">
                    <div class="drag-handle cursor-move text-gray-400 hover:text-gray-600">
                      <svg
                        class="h-4 w-4"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path d="M7 2a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM7 8a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM7 14a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM13 2a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM13 8a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM13 14a2 2 0 1 0 0 4 2 2 0 0 0 0-4z" />
                      </svg>
                    </div>
                    <span class="text-sm font-medium text-go4-secondary dark:text-white truncate">
                      {{ prompt.name }}
                    </span>
                    <span
                      v-if="prompt.is_system"
                      class="shrink-0 rounded bg-blue-100 px-1.5 py-0.5 text-[10px] text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                    >
                      System
                    </span>
                    <code class="shrink-0 text-[10px] text-go4-muted">{{ prompt.slug }}</code>
                  </div>
                  <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      class="rounded p-1 text-gray-400 hover:bg-gray-200 hover:text-gray-600 dark:hover:bg-gray-600"
                      title="Duplizieren"
                      @click.stop="openDuplicatePrompt(prompt)"
                    >
                      <svg
                        class="h-3.5 w-3.5"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      ><path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                      /></svg>
                    </button>
                    <button
                      v-if="!prompt.is_system"
                      class="rounded p-1 text-gray-400 hover:bg-red-100 hover:text-red-600"
                      title="Löschen"
                      @click.stop="handleDeletePrompt(prompt)"
                    >
                      <svg
                        class="h-3.5 w-3.5"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      ><path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                      /></svg>
                    </button>
                  </div>
                </div>
              </template>
            </draggable>
          </div>

          <!-- Productive Prompts Section -->
          <div class="p-4">
            <div class="mb-3 flex items-center justify-between">
              <h4 class="flex items-center gap-2 text-sm font-semibold text-go4-secondary dark:text-white">
                <svg
                  class="h-4 w-4 text-green-500"
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
                Productive Prompts
                <span class="rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-700 dark:bg-green-900/30 dark:text-green-400">
                  {{ prompts.productive.length }}
                </span>
              </h4>
              <button
                class="rounded px-2 py-1 text-xs text-go4-primary hover:bg-go4-primary/10"
                @click="openCreatePrompt('productive')"
              >
                + Neu
              </button>
            </div>
            <p class="mb-3 text-xs text-go4-muted">
              Prompts für automatisierte Nachrichten und Content
            </p>
            <div
              v-if="localProductivePrompts.length === 0"
              class="text-sm text-go4-muted italic"
            >
              Keine Productive-Prompts definiert
            </div>
            <draggable
              v-else
              :list="localProductivePrompts"
              item-key="id"
              handle=".drag-handle"
              ghost-class="bg-go4-primary/10"
              class="space-y-1"
              @end="onProductivePromptsReorder"
            >
              <template #item="{ element: prompt }">
                <div
                  class="group flex items-center justify-between rounded-lg border border-gray-100 bg-gray-50 px-3 py-2 hover:border-go4-primary/30 hover:bg-go4-primary/5 cursor-pointer transition dark:border-gray-600 dark:bg-gray-700/50"
                  @click="openEditPrompt(prompt)"
                >
                  <div class="flex items-center gap-2 min-w-0">
                    <div class="drag-handle cursor-move text-gray-400 hover:text-gray-600">
                      <svg
                        class="h-4 w-4"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path d="M7 2a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM7 8a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM7 14a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM13 2a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM13 8a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM13 14a2 2 0 1 0 0 4 2 2 0 0 0 0-4z" />
                      </svg>
                    </div>
                    <span class="text-sm font-medium text-go4-secondary dark:text-white truncate">
                      {{ prompt.name }}
                    </span>
                    <span
                      v-if="prompt.is_system"
                      class="shrink-0 rounded bg-blue-100 px-1.5 py-0.5 text-[10px] text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                    >
                      System
                    </span>
                    <code class="shrink-0 text-[10px] text-go4-muted">{{ prompt.slug }}</code>
                  </div>
                  <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      class="rounded p-1 text-gray-400 hover:bg-gray-200 hover:text-gray-600 dark:hover:bg-gray-600"
                      title="Duplizieren"
                      @click.stop="openDuplicatePrompt(prompt)"
                    >
                      <svg
                        class="h-3.5 w-3.5"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      ><path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                      /></svg>
                    </button>
                    <button
                      v-if="!prompt.is_system"
                      class="rounded p-1 text-gray-400 hover:bg-red-100 hover:text-red-600"
                      title="Löschen"
                      @click.stop="handleDeletePrompt(prompt)"
                    >
                      <svg
                        class="h-3.5 w-3.5"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      ><path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                      /></svg>
                    </button>
                  </div>
                </div>
              </template>
            </draggable>
          </div>
        </div>
      </div>
    </template>

    <!-- Onboarding Chat Modal -->
    <OnboardingChat
      :module="module"
      :visible="showOnboarding"
      @close="showOnboarding = false"
      @complete="handleOnboardingComplete"
    />

    <!-- Prompt Edit Modal -->
    <PromptEditModal
      v-if="showPromptModal"
      :module="module"
      :prompt="editingPrompt"
      :duplicate="isDuplicating"
      :default-type="newPromptType"
      @close="closePromptModal"
      @saved="handlePromptSaved"
    />
  </div>
</template>
