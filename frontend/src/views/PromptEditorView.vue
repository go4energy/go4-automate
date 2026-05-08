<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePromptStore } from '@/stores/prompts'
import PageHeader from '@/components/ui/PageHeader.vue'

const route = useRoute()
const router = useRouter()
const store = usePromptStore()

const isNew = computed(() => route.params.id === undefined)
const loading = ref(false)
const saving = ref(false)
const error = ref(null)
const testLoading = ref(false)
const testResult = ref(null)
const testError = ref(null)

const form = ref({
  slug: '',
  name: '',
  description: '',
  category: 'general',
  system_prompt: '',
  user_prompt: '',
  variables: [],
  output_format: 'text',
  provider: 'anthropic',
  model: 'claude-sonnet-4-5-20250929',
  temperature: 0.7,
  max_tokens: 2048,
  processing_mode: 'batch'
})

const testVariables = ref({})

const detectedVariables = computed(() => {
  const combined = (form.value.system_prompt || '') + ' ' + (form.value.user_prompt || '')
  const matches = combined.match(/\{\{(\w+)\}\}/g) || []
  return [...new Set(matches.map((m) => m.replace(/[{}]/g, '')))]
})

watch(detectedVariables, (vars) => {
  const current = testVariables.value
  const updated = {}
  vars.forEach((v) => {
    updated[v] = current[v] || ''
  })
  testVariables.value = updated
})

function addVariable() {
  form.value.variables.push({
    name: '',
    type: 'string',
    required: true,
    default: null,
    description: ''
  })
}

function removeVariable(index) {
  form.value.variables.splice(index, 1)
}

async function loadPrompt() {
  if (isNew.value) return
  loading.value = true
  error.value = null
  try {
    const data = await store.fetchPrompt(route.params.id)
    form.value = {
      slug: data.slug,
      name: data.name,
      description: data.description || '',
      category: data.category,
      system_prompt: data.system_prompt,
      user_prompt: data.user_prompt,
      variables: data.variables || [],
      output_format: data.output_format,
      provider: data.provider,
      model: data.model,
      temperature: data.temperature,
      max_tokens: data.max_tokens,
      processing_mode: data.processing_mode || 'batch'
    }
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  error.value = null
  try {
    const payload = { ...form.value }
    if (payload.variables.length === 0) {
      payload.variables = null
    }
    if (isNew.value) {
      const data = await store.addPrompt(payload)
      router.push(`/settings/prompts/${data.id}`)
    } else {
      await store.editPrompt(Number(route.params.id), payload)
    }
  } catch (err) {
    error.value = err.message
  } finally {
    saving.value = false
  }
}

async function handleDelete() {
  if (!confirm('Prompt wirklich loeschen?')) return
  try {
    await store.removePrompt(Number(route.params.id))
    router.push('/settings/prompts')
  } catch (err) {
    error.value = err.message
  }
}

async function handleNewVersion() {
  try {
    const data = await store.newVersion(Number(route.params.id))
    router.push(`/settings/prompts/${data.id}`)
  } catch (err) {
    error.value = err.message
  }
}

async function runTest() {
  testLoading.value = true
  testResult.value = null
  testError.value = null
  try {
    const data = await store.testPrompt(form.value.slug, testVariables.value)
    testResult.value = data
  } catch (err) {
    testError.value = err.message
  } finally {
    testLoading.value = false
  }
}

onMounted(() => {
  loadPrompt()
})
</script>

<template>
  <div>
    <!-- Header -->
    <PageHeader :title="isNew ? 'Neuer Prompt' : form.name || 'Prompt bearbeiten'">
      <template #actions>
        <span
          v-if="!isNew && store.currentPrompt"
          class="rounded-full bg-gray-100 dark:bg-gray-700 px-2 py-0.5 text-xs text-go4-muted dark:text-gray-400"
        >
          v{{ store.currentPrompt.version }}
        </span>
        <template v-if="!isNew">
          <button
            class="rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-sm text-go4-muted dark:text-gray-400 transition hover:bg-gray-50 dark:hover:bg-gray-700"
            @click="handleNewVersion"
          >
            Neue Version
          </button>
          <button
            class="rounded-lg border border-red-300 px-3 py-1.5 text-sm text-red-600 transition hover:bg-red-50 dark:border-red-700 dark:text-red-400 dark:hover:bg-red-900/20"
            @click="handleDelete"
          >
            Loeschen
          </button>
        </template>
        <button
          type="button"
          class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90 disabled:opacity-50"
          :disabled="saving"
          @click="save"
        >
          {{ saving ? 'Speichern…' : isNew ? 'Erstellen' : 'Speichern' }}
        </button>
      </template>
    </PageHeader>

    <!-- Loading -->
    <div
      v-if="loading"
      class="mt-8 flex items-center justify-center p-8"
    >
      <span class="text-go4-muted dark:text-gray-400">Laden...</span>
    </div>

    <!-- Error -->
    <div
      v-else-if="error"
      class="mt-4 rounded-lg bg-red-50 dark:bg-red-900/20 p-4 text-red-700 dark:text-red-400"
    >
      {{ error }}
    </div>

    <!-- Editor -->
    <div
      v-else
      class="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2"
    >
      <!-- Left: Form -->
      <div class="space-y-5">
        <!-- Basics -->
        <div class="rounded-lg bg-white dark:bg-gray-800 p-5 shadow-sm">
          <h2 class="mb-4 text-sm font-semibold text-go4-secondary dark:text-gray-100">
            Grunddaten
          </h2>
          <div class="space-y-3">
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="mb-1 block text-xs font-medium text-go4-muted dark:text-gray-400">Slug</label>
                <input
                  v-model="form.slug"
                  type="text"
                  :disabled="!isNew"
                  placeholder="my-prompt"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none disabled:bg-gray-100 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 dark:disabled:bg-gray-700"
                >
              </div>
              <div>
                <label class="mb-1 block text-xs font-medium text-go4-muted dark:text-gray-400">Name</label>
                <input
                  v-model="form.name"
                  type="text"
                  placeholder="Mein Prompt"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
                >
              </div>
            </div>
            <div>
              <label class="mb-1 block text-xs font-medium text-go4-muted dark:text-gray-400">Beschreibung</label>
              <input
                v-model="form.description"
                type="text"
                placeholder="Was macht dieser Prompt?"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
              >
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="mb-1 block text-xs font-medium text-go4-muted dark:text-gray-400">Kategorie</label>
                <select
                  v-model="form.category"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
                >
                  <option value="general">
                    General
                  </option>
                  <option value="content">
                    Content
                  </option>
                  <option value="analysis">
                    Analysis
                  </option>
                  <option value="email">
                    Email
                  </option>
                  <option value="chat">
                    Chat
                  </option>
                  <option value="research">
                    Research
                  </option>
                </select>
              </div>
              <div>
                <label class="mb-1 block text-xs font-medium text-go4-muted dark:text-gray-400">Output Format</label>
                <select
                  v-model="form.output_format"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
                >
                  <option value="text">
                    Text
                  </option>
                  <option value="json">
                    JSON
                  </option>
                </select>
              </div>
            </div>
          </div>
        </div>

        <!-- Prompts -->
        <div class="rounded-lg bg-white dark:bg-gray-800 p-5 shadow-sm">
          <h2 class="mb-4 text-sm font-semibold text-go4-secondary dark:text-gray-100">
            Prompts
          </h2>
          <div class="space-y-3">
            <div>
              <label class="mb-1 block text-xs font-medium text-go4-muted dark:text-gray-400">System Prompt</label>
              <textarea
                v-model="form.system_prompt"
                rows="4"
                placeholder="Du bist ein {{ROLE}} fuer {{COMPANY_NAME}}..."
                class="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm focus:border-go4-primary focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
              />
            </div>
            <div>
              <label class="mb-1 block text-xs font-medium text-go4-muted dark:text-gray-400">User Prompt</label>
              <textarea
                v-model="form.user_prompt"
                rows="8"
                placeholder="Erstelle einen {{content_type}} ueber {{topic}}..."
                class="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm focus:border-go4-primary focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
              />
            </div>
          </div>
        </div>

        <!-- Variables -->
        <div class="rounded-lg bg-white dark:bg-gray-800 p-5 shadow-sm">
          <div class="mb-4 flex items-center justify-between">
            <h2 class="text-sm font-semibold text-go4-secondary dark:text-gray-100">
              Variablen
            </h2>
            <button
              class="rounded-lg border border-gray-300 dark:border-gray-600 px-2 py-1 text-xs text-go4-muted dark:text-gray-400 transition hover:bg-gray-50 dark:hover:bg-gray-700"
              @click="addVariable"
            >
              + Variable
            </button>
          </div>
          <div
            v-if="form.variables.length === 0"
            class="text-xs text-go4-muted dark:text-gray-400"
          >
            Keine Variablen definiert.
          </div>
          <div
            v-else
            class="space-y-3"
          >
            <div
              v-for="(v, index) in form.variables"
              :key="index"
              class="rounded-lg border border-gray-200 dark:border-gray-700 p-3"
            >
              <div class="flex items-center gap-2">
                <input
                  v-model="v.name"
                  type="text"
                  placeholder="variable_name"
                  class="flex-1 rounded border border-gray-300 px-2 py-1 font-mono text-xs focus:border-go4-primary focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
                >
                <select
                  v-model="v.type"
                  class="rounded border border-gray-300 px-2 py-1 text-xs focus:border-go4-primary focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
                >
                  <option value="string">
                    String
                  </option>
                  <option value="number">
                    Number
                  </option>
                  <option value="boolean">
                    Boolean
                  </option>
                </select>
                <label class="flex items-center gap-1 text-xs dark:text-gray-300">
                  <input
                    v-model="v.required"
                    type="checkbox"
                    class="rounded"
                  >
                  Req
                </label>
                <button
                  class="text-xs text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
                  @click="removeVariable(index)"
                >
                  &times;
                </button>
              </div>
              <div class="mt-2 grid grid-cols-2 gap-2">
                <input
                  v-model="v.default"
                  type="text"
                  placeholder="Default"
                  class="rounded border border-gray-300 px-2 py-1 text-xs focus:border-go4-primary focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
                >
                <input
                  v-model="v.description"
                  type="text"
                  placeholder="Beschreibung"
                  class="rounded border border-gray-300 px-2 py-1 text-xs focus:border-go4-primary focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
                >
              </div>
            </div>
          </div>
        </div>

        <!-- LLM Config -->
        <div class="rounded-lg bg-white dark:bg-gray-800 p-5 shadow-sm">
          <h2 class="mb-4 text-sm font-semibold text-go4-secondary dark:text-gray-100">
            LLM Konfiguration
          </h2>
          <div class="space-y-3">
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="mb-1 block text-xs font-medium text-go4-muted dark:text-gray-400">Provider</label>
                <select
                  v-model="form.provider"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
                >
                  <option value="anthropic">
                    Anthropic
                  </option>
                  <option value="openai">
                    OpenAI
                  </option>
                </select>
              </div>
              <div>
                <label class="mb-1 block text-xs font-medium text-go4-muted dark:text-gray-400">Model</label>
                <input
                  v-model="form.model"
                  type="text"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
                >
              </div>
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="mb-1 block text-xs font-medium text-go4-muted dark:text-gray-400">
                  Temperature: {{ form.temperature }}
                </label>
                <input
                  v-model.number="form.temperature"
                  type="range"
                  min="0"
                  max="2"
                  step="0.1"
                  class="w-full"
                >
              </div>
              <div>
                <label class="mb-1 block text-xs font-medium text-go4-muted dark:text-gray-400">Max Tokens</label>
                <input
                  v-model.number="form.max_tokens"
                  type="number"
                  min="1"
                  max="16384"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
                >
              </div>
            </div>
            <div>
              <label class="mb-1 block text-xs font-medium text-go4-muted dark:text-gray-400">Verarbeitungsmodus</label>
              <select
                v-model="form.processing_mode"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
              >
                <option value="batch">
                  Alle Findings auf einmal (batch)
                </option>
                <option value="each">
                  Pro Finding einzeln (each)
                </option>
              </select>
              <p class="mt-1 text-xs text-go4-muted dark:text-gray-400">
                Batch: 1 LLM-Call mit allen Findings. Each: 1 LLM-Call pro Finding.
              </p>
            </div>
          </div>
        </div>

      </div>

      <!-- Right: Preview + Test -->
      <div class="space-y-5">
        <!-- Detected Variables Preview -->
        <div class="rounded-lg bg-white dark:bg-gray-800 p-5 shadow-sm">
          <h2 class="mb-3 text-sm font-semibold text-go4-secondary dark:text-gray-100">
            Erkannte Variablen
          </h2>
          <div
            v-if="detectedVariables.length === 0"
            class="text-xs text-go4-muted dark:text-gray-400"
          >
            Keine
            <code class="rounded bg-gray-100 dark:bg-gray-700 px-1">{'{{ VAR }}'}</code> Platzhalter
            in den Prompts gefunden.
          </div>
          <div
            v-else
            class="flex flex-wrap gap-2"
          >
            <span
              v-for="v in detectedVariables"
              :key="v"
              class="rounded-full bg-blue-50 dark:bg-blue-900/20 px-2.5 py-1 font-mono text-xs text-blue-700 dark:text-blue-400"
            >
              {{ v }}
            </span>
          </div>
        </div>

        <!-- Test Panel -->
        <div class="rounded-lg bg-white dark:bg-gray-800 p-5 shadow-sm">
          <h2 class="mb-3 text-sm font-semibold text-go4-secondary dark:text-gray-100">
            Test Panel
          </h2>
          <div
            v-if="!form.slug"
            class="text-xs text-go4-muted dark:text-gray-400"
          >
            Bitte zuerst einen Slug eingeben und den Prompt speichern.
          </div>
          <div
            v-else
            class="space-y-3"
          >
            <div
              v-for="v in detectedVariables"
              :key="v"
            >
              <label class="mb-1 block font-mono text-xs text-go4-muted dark:text-gray-400">{{
                v
              }}</label>
              <input
                v-model="testVariables[v]"
                type="text"
                :placeholder="v"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
              >
            </div>
            <button
              class="w-full rounded-lg bg-go4-secondary px-4 py-2 text-sm font-medium text-white transition hover:bg-go4-secondary/90 disabled:opacity-50"
              :disabled="testLoading || isNew"
              @click="runTest"
            >
              {{ testLoading ? 'Generiere...' : 'Testen' }}
            </button>
          </div>
        </div>

        <!-- Test Result -->
        <div
          v-if="testError"
          class="rounded-lg bg-red-50 dark:bg-red-900/20 p-4 text-sm text-red-700 dark:text-red-400"
        >
          {{ testError }}
        </div>
        <div
          v-if="testResult"
          class="rounded-lg bg-white dark:bg-gray-800 p-5 shadow-sm"
        >
          <div class="mb-3 flex items-center justify-between">
            <h2 class="text-sm font-semibold text-go4-secondary dark:text-gray-100">
              Ergebnis
            </h2>
            <span class="text-xs text-go4-muted dark:text-gray-400">
              {{ testResult.provider }} / {{ testResult.model }} (v{{ testResult.version }})
            </span>
          </div>
          <pre
            class="max-h-96 overflow-auto rounded-lg bg-gray-50 dark:bg-gray-800/50 p-4 font-mono text-xs leading-relaxed text-gray-800 dark:text-gray-200"
          >{{
              typeof testResult.result === 'object'
                ? JSON.stringify(testResult.result, null, 2)
                : testResult.result
          }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>
