<script setup>
/**
 * Slide-in editor for a single PipelinePrompt.
 *
 * Modes:
 *  - prompt is null + open: create mode (channel/slot pre-filled from props)
 *  - prompt has id: edit mode
 *
 * Emits:
 *  - close: drawer should be hidden
 *  - saved(prompt): a new/updated prompt
 *  - deleted(promptId)
 */
import { ref, watch, computed } from 'vue'
import {
  createPipelinePrompt,
  updatePipelinePrompt,
  deletePipelinePrompt,
  testPipelinePrompt,
} from '@/api/engagement'

const props = defineProps({
  open: { type: Boolean, default: false },
  pipelineId: { type: Number, required: true },
  prompt: { type: Object, default: null },        // existing prompt or null
  defaultChannel: { type: String, default: 'email' },
  defaultSlot: { type: String, default: 'initial' },
})

const emit = defineEmits(['close', 'saved', 'deleted'])

const channelOptions = [
  { value: 'email', label: '✉ Email' },
  { value: 'letter', label: '✉ Brief' },
  { value: 'whatsapp', label: '💬 WhatsApp' },
  { value: 'linkedin', label: '🔗 LinkedIn' },
  { value: 'phone', label: '📞 Telefon' },
]

const slotPresets = [
  'initial',
  'followup_1',
  'followup_2',
  'reply',
  'reply_positive',
  'reply_negative',
]

const modelOptions = [
  { value: '', label: 'Standard (Sonnet) — Default' },
  { value: 'claude-opus-4-7', label: 'Premium (Opus 4.7)' },
  { value: 'claude-sonnet-4-6', label: 'Standard (Sonnet 4.6)' },
  { value: 'claude-haiku-4-5-20251001', label: 'Bulk (Haiku 4.5)' },
]

// Common variable hints — clicking inserts at cursor
const variableHints = [
  '{{firmenname}}',
  '{{ort}}',
  '{{anrede_gf}}',
  '{{name_gf}}',
  '{{first_name}}',
  '{{last_name}}',
  '{{position}}',
  '{{homepage_zusammenfassung}}',
]

const form = ref({
  channel: props.defaultChannel,
  slot: props.defaultSlot,
  name: '',
  system_prompt: '',
  model: '',
  temperature: 0.7,
  max_tokens: 600,
  is_active: true,
  sort_order: 0,
})

const promptTextarea = ref(null)
const saving = ref(false)
const deleting = ref(false)
const testing = ref(false)
const error = ref(null)
const testOutput = ref('')
const testMeta = ref(null)
const testContactId = ref('')

const isEdit = computed(() => Boolean(props.prompt?.id))

watch(
  () => [props.open, props.prompt],
  ([open]) => {
    if (!open) return
    error.value = null
    testOutput.value = ''
    testMeta.value = null
    if (props.prompt) {
      form.value = { ...props.prompt, model: props.prompt.model || '' }
    } else {
      form.value = {
        channel: props.defaultChannel,
        slot: props.defaultSlot,
        name: '',
        system_prompt: '',
        model: '',
        temperature: 0.7,
        max_tokens: 600,
        is_active: true,
        sort_order: 0,
      }
    }
  },
  { immediate: true },
)

function insertVariable(token) {
  const ta = promptTextarea.value
  if (!ta) {
    form.value.system_prompt += token
    return
  }
  const start = ta.selectionStart
  const end = ta.selectionEnd
  const before = form.value.system_prompt.slice(0, start)
  const after = form.value.system_prompt.slice(end)
  form.value.system_prompt = before + token + after
  // Restore cursor after the inserted token
  setTimeout(() => {
    ta.focus()
    ta.selectionStart = ta.selectionEnd = start + token.length
  }, 0)
}

async function save() {
  if (!form.value.name.trim() || !form.value.system_prompt.trim()) {
    error.value = 'Name und System-Prompt sind Pflicht.'
    return
  }
  saving.value = true
  error.value = null
  try {
    const payload = {
      ...form.value,
      model: form.value.model || null,
    }
    let result
    if (isEdit.value) {
      const { data } = await updatePipelinePrompt(props.pipelineId, props.prompt.id, payload)
      result = data
    } else {
      const { data } = await createPipelinePrompt(props.pipelineId, payload)
      result = data
    }
    emit('saved', result)
    emit('close')
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    saving.value = false
  }
}

async function remove() {
  if (!isEdit.value) return
  if (!window.confirm(`Prompt "${form.value.name}" löschen?`)) return
  deleting.value = true
  error.value = null
  try {
    await deletePipelinePrompt(props.pipelineId, props.prompt.id)
    emit('deleted', props.prompt.id)
    emit('close')
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    deleting.value = false
  }
}

async function runTest() {
  if (!isEdit.value) {
    error.value = 'Bitte zuerst speichern, dann testen.'
    return
  }
  testing.value = true
  error.value = null
  testOutput.value = ''
  try {
    const payload = {
      contact_id: testContactId.value ? Number(testContactId.value) : null,
      variables: {},
    }
    const { data } = await testPipelinePrompt(props.pipelineId, props.prompt.id, payload)
    testOutput.value = data.output
    testMeta.value = { model: data.model_used, ms: data.duration_ms }
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    testing.value = false
  }
}
</script>

<template>
  <Transition
    enter-active-class="transition duration-200"
    enter-from-class="translate-x-full"
    enter-to-class="translate-x-0"
    leave-active-class="transition duration-150"
    leave-from-class="translate-x-0"
    leave-to-class="translate-x-full"
  >
    <aside
      v-if="open"
      class="fixed inset-y-0 right-0 z-40 flex w-full max-w-2xl flex-col border-l border-gray-200 bg-white shadow-xl dark:border-gray-700 dark:bg-gray-900"
    >
      <!-- Header -->
      <header class="flex items-center justify-between border-b border-gray-200 px-5 py-3 dark:border-gray-700">
        <div>
          <h3 class="text-base font-semibold text-gray-900 dark:text-gray-100">
            {{ isEdit ? 'Prompt bearbeiten' : 'Neuer Prompt' }}
          </h3>
          <p class="text-xs text-gray-500 dark:text-gray-400">
            Pipeline #{{ pipelineId }} · {{ form.channel }} · {{ form.slot }}
          </p>
        </div>
        <button
          type="button"
          class="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-800"
          @click="emit('close')"
        >
          <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </header>

      <!-- Body (scrollable) -->
      <div class="flex-1 overflow-y-auto px-5 py-4 space-y-5">
        <!-- Top fields -->
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">Kanal</label>
            <select v-model="form.channel" class="block w-full rounded-md border border-gray-300 bg-white px-2 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100">
              <option v-for="o in channelOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
            </select>
          </div>
          <div>
            <label class="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">Slot</label>
            <input
              v-model="form.slot"
              list="slot-presets"
              class="block w-full rounded-md border border-gray-300 bg-white px-2 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
            />
            <datalist id="slot-presets">
              <option v-for="s in slotPresets" :key="s" :value="s" />
            </datalist>
          </div>
        </div>

        <div>
          <label class="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">Name</label>
          <input
            v-model="form.name"
            placeholder="z.B. Email — Erstkontakt MFH"
            class="block w-full rounded-md border border-gray-300 bg-white px-2 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
          />
        </div>

        <div class="grid grid-cols-3 gap-3">
          <div class="col-span-2">
            <label class="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">Modell</label>
            <select v-model="form.model" class="block w-full rounded-md border border-gray-300 bg-white px-2 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100">
              <option v-for="o in modelOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
            </select>
          </div>
          <div>
            <label class="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">Temp</label>
            <input
              v-model.number="form.temperature"
              type="number" min="0" max="2" step="0.1"
              class="block w-full rounded-md border border-gray-300 bg-white px-2 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
            />
          </div>
        </div>

        <!-- Variable helpers -->
        <div>
          <label class="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">
            Variablen einfügen
          </label>
          <div class="flex flex-wrap gap-1.5">
            <button
              v-for="v in variableHints"
              :key="v"
              type="button"
              class="rounded-md border border-gray-200 bg-gray-50 px-2 py-0.5 text-xs font-mono text-gray-700 transition hover:border-go4-primary hover:text-go4-primary dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300"
              @click="insertVariable(v)"
            >
              {{ v }}
            </button>
          </div>
        </div>

        <!-- System prompt textarea -->
        <div>
          <label class="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">System-Prompt</label>
          <textarea
            ref="promptTextarea"
            v-model="form.system_prompt"
            rows="18"
            placeholder="Du bist ein erfahrener B2B-Texter…"
            class="block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-mono text-gray-900 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
          />
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">Max Tokens</label>
            <input
              v-model.number="form.max_tokens"
              type="number" min="50" max="4000" step="50"
              class="block w-full rounded-md border border-gray-300 bg-white px-2 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
            />
          </div>
          <div class="flex items-end">
            <label class="inline-flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
              <input v-model="form.is_active" type="checkbox" class="rounded border-gray-300" />
              Aktiv
            </label>
          </div>
        </div>

        <!-- Test panel -->
        <div class="rounded-lg border border-emerald-200 bg-emerald-50/40 p-3 dark:border-emerald-800/40 dark:bg-emerald-900/10">
          <div class="mb-2 flex items-center justify-between">
            <p class="text-xs font-semibold uppercase tracking-wide text-emerald-700 dark:text-emerald-300">
              💡 Test-Lauf
            </p>
            <button
              type="button"
              class="rounded-md bg-emerald-600 px-3 py-1 text-xs font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
              :disabled="testing || !isEdit"
              @click="runTest"
            >
              {{ testing ? 'Läuft…' : 'Testen' }}
            </button>
          </div>
          <p v-if="!isEdit" class="text-xs text-gray-500 dark:text-gray-400">
            Erst speichern, dann testen.
          </p>
          <div v-else class="space-y-2">
            <div>
              <label class="mb-1 block text-xs text-gray-600 dark:text-gray-400">
                Optional: Contact-ID für echte Variablen-Werte
              </label>
              <input
                v-model="testContactId"
                type="number"
                placeholder="z.B. 42 — leer = leere Variablen"
                class="block w-full rounded-md border border-gray-200 bg-white px-2 py-1 text-sm dark:border-gray-700 dark:bg-gray-800 dark:text-gray-100"
              />
            </div>
            <div v-if="testOutput" class="space-y-1">
              <p class="text-xs text-gray-500 dark:text-gray-400">
                {{ testMeta?.model }} · {{ testMeta?.ms }} ms
              </p>
              <pre class="whitespace-pre-wrap rounded-md border border-gray-200 bg-white p-3 text-sm text-gray-800 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-100">{{ testOutput }}</pre>
            </div>
          </div>
        </div>

        <!-- Error -->
        <div v-if="error" class="rounded-md bg-red-50 p-2 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-300">
          {{ error }}
        </div>
      </div>

      <!-- Footer -->
      <footer class="flex items-center justify-between border-t border-gray-200 px-5 py-3 dark:border-gray-700">
        <button
          v-if="isEdit"
          type="button"
          class="rounded-md px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 disabled:opacity-50 dark:hover:bg-red-900/20"
          :disabled="deleting"
          @click="remove"
        >
          {{ deleting ? 'Lösche…' : 'Löschen' }}
        </button>
        <span v-else />
        <div class="flex items-center gap-2">
          <button
            type="button"
            class="rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-800"
            @click="emit('close')"
          >
            Abbrechen
          </button>
          <button
            type="button"
            class="rounded-md bg-go4-primary px-3 py-1.5 text-sm font-medium text-white hover:bg-go4-primary-dark disabled:opacity-50"
            :disabled="saving"
            @click="save"
          >
            {{ saving ? 'Speichere…' : 'Speichern' }}
          </button>
        </div>
      </footer>
    </aside>
  </Transition>
</template>
