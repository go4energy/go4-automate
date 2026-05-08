<script setup>
/**
 * Compact card for triggering the bulk Brain run on a pipeline.
 *
 * Shows:
 *  - Drafts counter (out of total enrollments)
 *  - "Brain durchlaufen lassen" button (channel + slot pickers)
 *  - Live progress + cache telemetry while running
 *
 * Lives in the right column of the Pipeline-Übersicht-Tab next to
 * ChannelPromptList.
 */
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import {
  triggerBulkBrain,
  triggerAbBrain,
  getBulkBrainStatus,
  stopBulkBrain,
  listDrafts,
} from '@/api/engagement'

const props = defineProps({
  pipelineId: { type: Number, required: true },
  totalEnrollments: { type: Number, default: 0 },
})

const emit = defineEmits(['drafts-changed'])

const status = ref({ status: 'idle' })
const drafts = ref([])
const loadingDrafts = ref(false)
const channel = ref('email')
const slot = ref('initial')
const limit = ref(10)
const showAbDialog = ref(false)
const abModelB = ref('claude-opus-4-7')
const error = ref(null)

let pollHandle = null

const isRunning = computed(() => status.value?.status === 'running')
const isDone = computed(() => status.value?.status === 'done')
const isFailed = computed(() => status.value?.status === 'failed')
const draftsCount = computed(() => drafts.value.length)

function fmtNumber(n) {
  return (n || 0).toLocaleString('de-DE')
}

function fmtCost(usage) {
  // Rough Sonnet pricing: $0.30/M cache-read, $3.75/M cache-write, $3/M input, $15/M output
  if (!usage) return '0,00 $'
  const cents =
    (usage.cache_read_total || 0) * 0.0003 +
    (usage.cache_create_total || 0) * 0.00375 +
    (usage.input_total || 0) * 0.003 +
    (usage.output_total || 0) * 0.015
  return `${(cents / 1000).toFixed(2)} $`
}

const progressPercent = computed(() => {
  const t = status.value?.total || 0
  const d = status.value?.done || 0
  if (!t) return 0
  return Math.round((d / t) * 100)
})

async function refreshStatus() {
  try {
    const { data } = await getBulkBrainStatus(props.pipelineId)
    status.value = data
  } catch (e) {
    // ignore — pipeline might be missing for a moment
  }
}

async function refreshDrafts() {
  loadingDrafts.value = true
  try {
    const { data } = await listDrafts(props.pipelineId, channel.value)
    drafts.value = data
    emit('drafts-changed', data.length)
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    loadingDrafts.value = false
  }
}

function startPolling() {
  if (pollHandle) return
  pollHandle = setInterval(async () => {
    await refreshStatus()
    if (status.value?.status !== 'running') {
      stopPolling()
      await refreshDrafts()
    }
  }, 2000)
}

function stopPolling() {
  if (pollHandle) {
    clearInterval(pollHandle)
    pollHandle = null
  }
}

watch(isRunning, (running) => {
  if (running) startPolling()
  else stopPolling()
})

async function start() {
  error.value = null
  try {
    await triggerBulkBrain(props.pipelineId, {
      channel: channel.value,
      slot: slot.value,
      limit: limit.value > 0 ? Number(limit.value) : null,
    })
    await refreshStatus()
    startPolling()
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  }
}

async function startAb() {
  error.value = null
  showAbDialog.value = false
  try {
    await triggerAbBrain(props.pipelineId, {
      channel: channel.value,
      slot: slot.value,
      variant_b_model: abModelB.value,
      limit: limit.value > 0 ? Number(limit.value) : null,
    })
    await refreshStatus()
    startPolling()
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  }
}

async function stop() {
  error.value = null
  try {
    await stopBulkBrain(props.pipelineId)
    await refreshStatus()
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  }
}

onMounted(async () => {
  await refreshStatus()
  await refreshDrafts()
  if (status.value?.status === 'running') startPolling()
})

onBeforeUnmount(() => stopPolling())
</script>

<template>
  <div class="rounded-lg bg-white p-5 shadow dark:bg-gray-800">
    <div class="mb-3 flex items-center justify-between">
      <h3 class="text-base font-semibold text-gray-900 dark:text-gray-100">
        🧠 Brain-Bulk-Run
      </h3>
      <span
        v-if="isRunning"
        class="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700 dark:bg-amber-900/40 dark:text-amber-300"
      >
        Läuft
      </span>
      <span
        v-else-if="isDone"
        class="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300"
      >
        Fertig
      </span>
      <span
        v-else-if="isFailed"
        class="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700 dark:bg-red-900/40 dark:text-red-300"
      >
        Fehler
      </span>
    </div>

    <!-- Counter row -->
    <div class="mb-4 grid grid-cols-2 gap-3 text-sm">
      <div class="rounded-md border border-gray-200 bg-gray-50 px-3 py-2 dark:border-gray-700 dark:bg-gray-900/40">
        <div class="text-xs text-gray-500 dark:text-gray-400">Enrollments</div>
        <div class="text-lg font-semibold text-gray-900 dark:text-gray-100">
          {{ fmtNumber(totalEnrollments) }}
        </div>
      </div>
      <div class="rounded-md border border-gray-200 bg-gray-50 px-3 py-2 dark:border-gray-700 dark:bg-gray-900/40">
        <div class="text-xs text-gray-500 dark:text-gray-400">Drafts bereit</div>
        <div class="text-lg font-semibold text-emerald-600 dark:text-emerald-400">
          {{ fmtNumber(draftsCount) }}
        </div>
      </div>
    </div>

    <!-- Progress bar (visible while running or just-done) -->
    <div v-if="isRunning || isDone || isFailed" class="mb-4 space-y-2">
      <div class="flex items-center justify-between text-xs text-gray-600 dark:text-gray-400">
        <span>{{ status.done || 0 }} / {{ status.total || 0 }} ({{ progressPercent }} %)</span>
        <span v-if="status.model" class="font-mono text-[10px]">
          <span v-if="status.phase" class="mr-1 rounded bg-gray-200 px-1 font-bold dark:bg-gray-600">
            Variante {{ status.phase }}
          </span>
          {{ status.model }}
        </span>
      </div>
      <div class="h-2 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
        <div
          class="h-full bg-emerald-500 transition-all"
          :style="`width: ${progressPercent}%`"
        />
      </div>
      <div class="grid grid-cols-2 gap-2 text-[11px] text-gray-500 dark:text-gray-400">
        <div>📥 Cache-Reads: {{ fmtNumber(status.cache_read_total) }}</div>
        <div>🆕 Cache-Writes: {{ fmtNumber(status.cache_create_total) }}</div>
        <div>📨 Input: {{ fmtNumber(status.input_total) }}</div>
        <div>📤 Output: {{ fmtNumber(status.output_total) }}</div>
        <div class="col-span-2 font-medium text-gray-700 dark:text-gray-300">
          ≈ {{ fmtCost(status) }}
        </div>
      </div>
      <div
        v-if="status.errors?.length"
        class="rounded-md bg-red-50 p-2 text-xs text-red-700 dark:bg-red-900/20 dark:text-red-300"
      >
        {{ status.errors.length }} Fehler — siehe Backend-Log
      </div>
    </div>

    <!-- Stop-Button während des Runs -->
    <div v-if="isRunning" class="mb-3">
      <button
        type="button"
        class="w-full rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm font-medium text-red-700 hover:bg-red-100 dark:border-red-700 dark:bg-red-900/30 dark:text-red-300 dark:hover:bg-red-900/50"
        @click="stop"
      >
        ⏸ Bulk-Run stoppen (bisherige Drafts bleiben)
      </button>
    </div>

    <!-- Controls -->
    <div v-if="!isRunning" class="space-y-2">
      <div class="grid grid-cols-2 gap-2">
        <select
          v-model="channel"
          class="rounded-md border border-gray-300 bg-white px-2 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
        >
          <option value="email">✉ Email</option>
          <option value="letter">✉ Brief</option>
          <option value="linkedin">🔗 LinkedIn</option>
          <option value="whatsapp">💬 WhatsApp</option>
        </select>
        <input
          v-model="slot"
          list="slot-options"
          class="rounded-md border border-gray-300 bg-white px-2 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
        />
        <datalist id="slot-options">
          <option value="initial" />
          <option value="followup_1" />
          <option value="followup_2" />
          <option value="reply" />
        </datalist>
      </div>
      <div class="flex items-center gap-2">
        <label class="text-xs text-gray-600 dark:text-gray-400">Limit:</label>
        <input
          v-model.number="limit"
          type="number"
          min="0"
          class="w-20 rounded-md border border-gray-300 bg-white px-2 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
          placeholder="alle"
        />
        <span class="text-[11px] text-gray-500 dark:text-gray-400">
          0 = alle Enrollments
        </span>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <button
          type="button"
          class="flex-1 rounded-md bg-go4-primary px-3 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark"
          @click="start"
        >
          Brain durchlaufen lassen
        </button>
        <button
          type="button"
          class="rounded-md border border-gray-300 px-3 py-2 text-xs font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700"
          title="Pro Enrollment 2 Drafts: A=Standard, B=alternatives Modell"
          @click="showAbDialog = true"
        >
          A/B mit anderem Modell…
        </button>
      </div>
      <p class="text-[11px] text-gray-500 dark:text-gray-400">
        Generiert Drafts nur für Enrollments, die noch keine offene Email-Action haben. Bestehende Drafts bleiben.
      </p>
    </div>

    <!-- Error -->
    <div v-if="error" class="mt-3 rounded-md bg-red-50 p-2 text-xs text-red-700 dark:bg-red-900/20 dark:text-red-300">
      {{ error }}
    </div>

    <!-- A/B Dialog -->
    <div
      v-if="showAbDialog"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      @click.self="showAbDialog = false"
    >
      <div class="w-full max-w-md rounded-lg bg-white p-5 shadow-xl dark:bg-gray-800">
        <h3 class="mb-2 text-base font-semibold text-gray-900 dark:text-gray-100">A/B-Variantengenerierung</h3>
        <p class="mb-3 text-xs text-gray-600 dark:text-gray-400">
          Generiert <strong>2 Drafts pro Enrollment</strong> — Variante A mit dem Standardmodell des Prompts,
          Variante B mit dem unten gewählten alternativen Modell. Du kannst pro Empfänger entscheiden,
          welche Variante gesendet wird.
        </p>
        <label class="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">Variante B — Modell</label>
        <select
          v-model="abModelB"
          class="mb-4 w-full rounded-md border border-gray-300 bg-white px-2 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
        >
          <option value="claude-opus-4-7">Premium (Opus 4.7)</option>
          <option value="claude-sonnet-4-6">Standard (Sonnet 4.6)</option>
          <option value="claude-haiku-4-5-20251001">Bulk (Haiku 4.5)</option>
        </select>
        <div class="flex justify-end gap-2">
          <button
            type="button"
            class="rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700"
            @click="showAbDialog = false"
          >
            Abbrechen
          </button>
          <button
            type="button"
            class="rounded-md bg-go4-primary px-3 py-1.5 text-sm font-medium text-white hover:bg-go4-primary-dark"
            @click="startAb"
          >
            A/B starten
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
