<script setup>
import { ref, computed, watch } from 'vue'
import { createPrompt, updatePrompt, renderPrompt } from '@/api/ai'

const props = defineProps({
  module: { type: String, required: true },
  prompt: { type: Object, default: null },
  duplicate: { type: Boolean, default: false },
  defaultType: { type: String, default: 'productive' }
})

const emit = defineEmits(['close', 'saved'])

const isEdit = computed(() => !!props.prompt && !props.duplicate)
const title = computed(() => {
  if (props.duplicate) return 'Prompt duplizieren'
  if (isEdit.value) return 'Prompt bearbeiten'
  return 'Neuer Prompt'
})

const form = ref({
  slug: '',
  name: '',
  prompt_type: 'productive',
  system_prompt: '',
  user_prompt: '',
  provider: 'anthropic',
  model: 'claude-sonnet-4-20250514',
  temperature: 0.7,
  max_tokens: 2048
})

// Initialize form with prompt data
watch(
  () => props.prompt,
  (prompt) => {
    if (prompt) {
      form.value = {
        slug: props.duplicate ? `${prompt.slug}_copy` : prompt.slug,
        name: props.duplicate ? `${prompt.name} (Kopie)` : prompt.name,
        prompt_type: prompt.prompt_type || 'productive',
        system_prompt: prompt.system_prompt || '',
        user_prompt: prompt.user_prompt || '',
        provider: prompt.provider || 'anthropic',
        model: prompt.model || 'claude-sonnet-4-20250514',
        temperature: prompt.temperature ?? 0.7,
        max_tokens: prompt.max_tokens || 2048
      }
    } else {
      // Reset form for new prompt
      form.value = {
        slug: '',
        name: '',
        prompt_type: props.defaultType,
        system_prompt: '',
        user_prompt: '',
        provider: 'anthropic',
        model: 'claude-sonnet-4-20250514',
        temperature: 0.7,
        max_tokens: 2048
      }
    }
  },
  { immediate: true }
)

const loading = ref(false)
const error = ref(null)
const activeTab = ref('content')
const previewResult = ref(null)
const previewLoading = ref(false)

const tabs = [
  { key: 'content', label: 'Inhalt' },
  { key: 'settings', label: 'Einstellungen' },
  { key: 'preview', label: 'Vorschau' }
]

const providers = [
  { value: 'anthropic', label: 'Anthropic (Claude)' },
  { value: 'openai', label: 'OpenAI (GPT)' }
]

const models = computed(() => {
  if (form.value.provider === 'anthropic') {
    return [
      { value: 'claude-sonnet-4-20250514', label: 'Claude Sonnet 4' },
      { value: 'claude-3-5-sonnet-20241022', label: 'Claude 3.5 Sonnet' },
      { value: 'claude-3-haiku-20240307', label: 'Claude 3 Haiku (schnell)' }
    ]
  }
  return [
    { value: 'gpt-4o', label: 'GPT-4o' },
    { value: 'gpt-4o-mini', label: 'GPT-4o Mini (schnell)' },
    { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' }
  ]
})

async function handleSubmit() {
  loading.value = true
  error.value = null

  try {
    const data = {
      slug: form.value.slug,
      name: form.value.name,
      prompt_type: form.value.prompt_type,
      system_prompt: form.value.system_prompt,
      user_prompt: form.value.user_prompt,
      provider: form.value.provider,
      model: form.value.model,
      temperature: form.value.temperature,
      max_tokens: form.value.max_tokens
    }

    if (isEdit.value) {
      await updatePrompt(props.module, props.prompt.id, data)
    } else {
      await createPrompt(props.module, data)
    }
    emit('saved')
  } catch (err) {
    error.value = err.response?.data?.detail || err.message || 'Fehler beim Speichern'
  } finally {
    loading.value = false
  }
}

async function loadPreview() {
  if (!form.value.slug && !isEdit.value) {
    previewResult.value = { error: 'Bitte zuerst einen Slug eingeben' }
    return
  }

  previewLoading.value = true
  previewResult.value = null

  try {
    // For new prompts, just show the raw content
    if (!isEdit.value) {
      previewResult.value = {
        system_prompt: form.value.system_prompt,
        user_prompt: form.value.user_prompt,
        note: 'Vorschau ohne Variable-Substitution (neuer Prompt)'
      }
    } else {
      const { data } = await renderPrompt(props.module, props.prompt.slug)
      previewResult.value = data
    }
  } catch (err) {
    previewResult.value = { error: err.response?.data?.detail || 'Fehler beim Laden' }
  } finally {
    previewLoading.value = false
  }
}

// Load preview when switching to preview tab
watch(
  () => activeTab.value,
  (tab) => {
    if (tab === 'preview') {
      loadPreview()
    }
  }
)
</script>

<template>
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
    @click.self="emit('close')"
  >
    <div
      class="flex max-h-[90vh] w-full max-w-4xl flex-col overflow-hidden rounded-xl bg-white shadow-2xl dark:bg-gray-800"
    >
      <!-- Header -->
      <div
        class="flex items-center justify-between border-b border-gray-200 px-6 py-4 dark:border-gray-700"
      >
        <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
          {{ title }}
        </h2>
        <button
          class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          @click="emit('close')"
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

      <!-- Tabs -->
      <div class="border-b border-gray-200 px-6 dark:border-gray-700">
        <nav class="-mb-px flex gap-6">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            class="border-b-2 py-3 text-sm font-medium transition-colors"
            :class="
              activeTab === tab.key
                ? 'border-go4-primary text-go4-primary'
                : 'border-transparent text-go4-muted hover:border-gray-300 hover:text-go4-secondary'
            "
            @click="activeTab = tab.key"
          >
            {{ tab.label }}
          </button>
        </nav>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto p-6">
        <form @submit.prevent="handleSubmit">
          <!-- Error -->
          <div
            v-if="error"
            class="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600 dark:bg-red-900/30 dark:text-red-400"
          >
            {{ error }}
          </div>

          <!-- Content Tab -->
          <div
            v-show="activeTab === 'content'"
            class="space-y-4"
          >
            <!-- Basic Info -->
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Slug (ID)
                </label>
                <input
                  v-model="form.slug"
                  type="text"
                  required
                  pattern="[a-z0-9_]+"
                  :disabled="isEdit"
                  placeholder="z.B. connection_request"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-mono dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 disabled:bg-gray-100 disabled:dark:bg-gray-800"
                >
                <p class="mt-1 text-xs text-go4-muted">
                  Nur Kleinbuchstaben, Zahlen, Unterstriche
                </p>
              </div>
              <div>
                <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Name
                </label>
                <input
                  v-model="form.name"
                  type="text"
                  required
                  placeholder="z.B. Kontaktanfrage"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
                >
              </div>
            </div>

            <div>
              <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                Typ
              </label>
              <select
                v-model="form.prompt_type"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
              >
                <option value="setup">
                  Setup (Onboarding/Konfiguration)
                </option>
                <option value="productive">
                  Productive (Automatisierung)
                </option>
              </select>
            </div>

            <!-- System Prompt -->
            <div>
              <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                System Prompt
              </label>
              <textarea
                v-model="form.system_prompt"
                rows="6"
                placeholder="Anweisungen fuer das KI-Modell..."
                class="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
              />
              <p class="mt-1 text-xs text-go4-muted">
                Definiert das Verhalten und die Rolle der KI
              </p>
            </div>

            <!-- User Prompt -->
            <div>
              <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                User Prompt / Template
              </label>
              <textarea
                v-model="form.user_prompt"
                rows="8"
                placeholder="Der eigentliche Prompt mit {{variablen}}..."
                class="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
              />
              <p class="mt-1 text-xs text-go4-muted">
                Verwende
                <code
                  v-pre
                  class="rounded bg-gray-100 px-1 dark:bg-gray-700"
                >{{ variable }}</code>
                fuer Platzhalter
              </p>
            </div>
          </div>

          <!-- Settings Tab -->
          <div
            v-show="activeTab === 'settings'"
            class="space-y-4"
          >
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Provider
                </label>
                <select
                  v-model="form.provider"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
                >
                  <option
                    v-for="p in providers"
                    :key="p.value"
                    :value="p.value"
                  >
                    {{ p.label }}
                  </option>
                </select>
              </div>
              <div>
                <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Modell
                </label>
                <select
                  v-model="form.model"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
                >
                  <option
                    v-for="m in models"
                    :key="m.value"
                    :value="m.value"
                  >
                    {{ m.label }}
                  </option>
                </select>
              </div>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Temperature ({{ form.temperature }})
                </label>
                <input
                  v-model.number="form.temperature"
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  class="w-full"
                >
                <p class="mt-1 text-xs text-go4-muted">
                  0 = deterministisch, 1 = kreativ
                </p>
              </div>
              <div>
                <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Max Tokens
                </label>
                <input
                  v-model.number="form.max_tokens"
                  type="number"
                  min="100"
                  max="8192"
                  step="100"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
                >
                <p class="mt-1 text-xs text-go4-muted">
                  Maximale Laenge der Antwort
                </p>
              </div>
            </div>
          </div>

          <!-- Preview Tab -->
          <div
            v-show="activeTab === 'preview'"
            class="space-y-4"
          >
            <div
              v-if="previewLoading"
              class="py-8 text-center text-go4-muted"
            >
              Lade Vorschau...
            </div>

            <div
              v-else-if="previewResult?.error"
              class="rounded-lg bg-red-50 p-4 text-red-700 dark:bg-red-900/20"
            >
              {{ previewResult.error }}
            </div>

            <template v-else-if="previewResult">
              <div
                v-if="previewResult.note"
                class="rounded-lg bg-blue-50 p-3 text-sm text-blue-700 dark:bg-blue-900/20 dark:text-blue-300"
              >
                {{ previewResult.note }}
              </div>

              <div>
                <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                  System Prompt (gerendert)
                </label>
                <pre
                  class="max-h-48 overflow-auto rounded-lg bg-gray-100 p-3 text-sm dark:bg-gray-700"
                >{{ previewResult.system_prompt || '(leer)' }}</pre>
              </div>

              <div>
                <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                  User Prompt (gerendert)
                </label>
                <pre
                  class="max-h-48 overflow-auto rounded-lg bg-gray-100 p-3 text-sm dark:bg-gray-700"
                >{{ previewResult.user_prompt || '(leer)' }}</pre>
              </div>
            </template>

            <button
              type="button"
              class="rounded-lg border border-gray-300 px-4 py-2 text-sm hover:bg-gray-100 dark:border-gray-600 dark:hover:bg-gray-700"
              @click="loadPreview"
            >
              Vorschau neu laden
            </button>
          </div>
        </form>
      </div>

      <!-- Footer -->
      <div class="flex justify-end gap-3 border-t border-gray-200 px-6 py-4 dark:border-gray-700">
        <button
          type="button"
          class="rounded-lg px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700"
          @click="emit('close')"
        >
          Abbrechen
        </button>
        <button
          :disabled="loading"
          class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary/90 disabled:opacity-50"
          @click="handleSubmit"
        >
          {{ loading ? 'Speichern...' : 'Speichern' }}
        </button>
      </div>
    </div>
  </div>
</template>
