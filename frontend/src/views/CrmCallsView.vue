<script setup>
import { ref, computed, onMounted } from 'vue'
import { useCrmStore } from '@/stores/crm'
import PageHeader from '@/components/ui/PageHeader.vue'

const store = useCrmStore()

const selectedCall = ref(null)
const showLogModal = ref(false)
const generatingScript = ref(null)
const loggingCall = ref(false)

// Log form
const logForm = ref({
  outcome: '',
  duration_seconds: null,
  notes: '',
  follow_up_date: null,
  deal_id: null
})

const priorityConfig = {
  urgent: { label: 'Dringend', class: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300' },
  high: { label: 'Hoch', class: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300' },
  normal: { label: 'Normal', class: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300' },
  low: { label: 'Niedrig', class: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300' }
}

const outcomeOptions = [
  { value: 'answered', label: 'Gespräch geführt', icon: '✓' },
  { value: 'qualified', label: 'Qualifiziert', icon: '★' },
  { value: 'callback', label: 'Rückruf vereinbart', icon: '↻' },
  { value: 'no_answer', label: 'Nicht erreicht', icon: '✗' },
  { value: 'voicemail', label: 'Mailbox', icon: '✉' },
  { value: 'not_interested', label: 'Kein Interesse', icon: '−' },
  { value: 'wrong_number', label: 'Falsche Nummer', icon: '!' }
]

const stats = computed(() => store.callStats || {})

onMounted(async () => {
  await Promise.all([store.fetchCalls(), store.fetchCallStats()])
})

function formatDate(dateString) {
  if (!dateString) return ''
  const date = new Date(dateString)
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const dateOnly = new Date(date.getFullYear(), date.getMonth(), date.getDate())

  if (dateOnly.getTime() === today.getTime()) return 'Heute'
  if (dateOnly < today) return 'Überfällig'

  const tomorrow = new Date(today)
  tomorrow.setDate(tomorrow.getDate() + 1)
  if (dateOnly.getTime() === tomorrow.getTime()) return 'Morgen'

  return date.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' })
}

function isOverdue(call) {
  if (!call.due_at) return false
  return new Date(call.due_at) < new Date()
}

async function handleGenerateScript(call) {
  generatingScript.value = call.id
  try {
    await store.generateScript(call.id)
    selectedCall.value = store.calls.find((c) => c.id === call.id) || call
  } catch {
    // Error handled in store
  } finally {
    generatingScript.value = null
  }
}

function openLogModal(call) {
  selectedCall.value = call
  logForm.value = {
    outcome: '',
    duration_seconds: null,
    notes: '',
    follow_up_date: null,
    deal_id: null
  }
  showLogModal.value = true
}

async function submitLog() {
  if (!logForm.value.outcome || !selectedCall.value) return
  loggingCall.value = true
  try {
    await store.submitCallLog(selectedCall.value.id, logForm.value)
    showLogModal.value = false
    selectedCall.value = null
  } catch {
    // Error handled in store
  } finally {
    loggingCall.value = false
  }
}

function selectCall(call) {
  selectedCall.value = selectedCall.value?.id === call.id ? null : call
}
</script>

<template>
  <div>
    <PageHeader
      title="Anruf-Queue"
    />

    <!-- Stats Cards -->
    <div class="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
      <div class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
        <p class="text-sm text-gray-500 dark:text-gray-400">
          Ausstehend
        </p>
        <p class="mt-1 text-2xl font-semibold text-gray-900 dark:text-gray-100">
          {{ stats.total_pending || 0 }}
        </p>
      </div>
      <div class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
        <p class="text-sm text-gray-500 dark:text-gray-400">
          Heute fällig
        </p>
        <p class="mt-1 text-2xl font-semibold text-blue-600 dark:text-blue-400">
          {{ stats.due_today || 0 }}
        </p>
      </div>
      <div class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
        <p class="text-sm text-gray-500 dark:text-gray-400">
          Überfällig
        </p>
        <p class="mt-1 text-2xl font-semibold text-red-600 dark:text-red-400">
          {{ stats.overdue || 0 }}
        </p>
      </div>
      <div class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
        <p class="text-sm text-gray-500 dark:text-gray-400">
          Heute erledigt
        </p>
        <p class="mt-1 text-2xl font-semibold text-green-600 dark:text-green-400">
          {{ stats.completed_today || 0 }}
        </p>
      </div>
    </div>

    <!-- Loading -->
    <div
      v-if="store.loading"
      class="mt-6 flex items-center justify-center p-12"
    >
      <span class="text-go4-muted dark:text-gray-400">Laden...</span>
    </div>

    <!-- Error -->
    <div
      v-else-if="store.error"
      class="mt-6 rounded-lg bg-red-50 p-4 text-red-700 dark:bg-red-900/20 dark:text-red-400"
    >
      {{ store.error }}
    </div>

    <!-- Empty State -->
    <div
      v-else-if="store.calls.length === 0"
      class="mt-6 flex flex-col items-center justify-center rounded-lg border border-dashed border-gray-300 p-12 dark:border-gray-600"
    >
      <svg
        class="mb-4 h-12 w-12 text-gray-300 dark:text-gray-600"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"
        />
      </svg>
      <h3 class="mb-1 text-lg font-medium text-gray-900 dark:text-gray-100">
        Keine Anrufe in der Queue
      </h3>
      <p class="text-sm text-gray-500 dark:text-gray-400">
        Das Engagement-Brain erstellt Anruf-Aktionen automatisch.
      </p>
    </div>

    <!-- Call Queue + Detail Split -->
    <div
      v-else
      class="mt-6 grid gap-6"
      :class="selectedCall ? 'grid-cols-1 lg:grid-cols-2' : 'grid-cols-1'"
    >
      <!-- Call List -->
      <div class="divide-y divide-gray-100 rounded-lg border border-gray-200 bg-white dark:divide-gray-700 dark:border-gray-700 dark:bg-gray-800">
        <div
          v-for="call in store.calls"
          :key="call.id"
          class="flex cursor-pointer items-start gap-4 p-4 transition-colors hover:bg-gray-50 dark:hover:bg-gray-700/50"
          :class="{ 'bg-blue-50 dark:bg-blue-900/20': selectedCall?.id === call.id }"
          @click="selectCall(call)"
        >
          <!-- Phone Icon -->
          <div
            class="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full"
            :class="isOverdue(call) ? 'bg-red-100 text-red-600 dark:bg-red-900/30' : 'bg-blue-100 text-blue-600 dark:bg-blue-900/30'"
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
                d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"
              />
            </svg>
          </div>

          <!-- Content -->
          <div class="min-w-0 flex-1">
            <div class="flex items-start justify-between gap-2">
              <div>
                <p class="font-medium text-gray-900 dark:text-gray-100">
                  {{ call.contact_name || 'Unbekannt' }}
                </p>
                <p
                  v-if="call.contact_company"
                  class="text-sm text-gray-500 dark:text-gray-400"
                >
                  {{ call.contact_company }}
                </p>
              </div>
              <div class="flex flex-shrink-0 items-center gap-2">
                <span
                  v-if="call.due_at"
                  class="text-sm"
                  :class="isOverdue(call) ? 'font-medium text-red-500' : 'text-gray-400 dark:text-gray-500'"
                >
                  {{ formatDate(call.due_at) }}
                </span>
                <span
                  class="rounded-full px-2 py-0.5 text-xs"
                  :class="priorityConfig[call.priority]?.class"
                >
                  {{ priorityConfig[call.priority]?.label }}
                </span>
              </div>
            </div>

            <div class="mt-1 flex items-center gap-3">
              <span
                v-if="call.contact_phone"
                class="text-sm font-mono text-gray-600 dark:text-gray-300"
              >
                {{ call.contact_phone }}
              </span>
              <span
                v-if="call.pipeline_name"
                class="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-500 dark:bg-gray-700 dark:text-gray-400"
              >
                {{ call.pipeline_name }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Detail Panel -->
      <div
        v-if="selectedCall"
        class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800"
      >
        <div class="flex items-start justify-between">
          <div>
            <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
              {{ selectedCall.contact_name || 'Unbekannt' }}
            </h3>
            <p
              v-if="selectedCall.contact_company"
              class="text-sm text-gray-500 dark:text-gray-400"
            >
              {{ selectedCall.contact_company }}
            </p>
          </div>
          <button
            type="button"
            class="text-gray-400 hover:text-gray-500"
            @click="selectedCall = null"
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

        <!-- Contact Info -->
        <div class="mt-4 space-y-2">
          <div
            v-if="selectedCall.contact_phone"
            class="flex items-center gap-2"
          >
            <svg
              class="h-4 w-4 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"
              />
            </svg>
            <a
              :href="`tel:${selectedCall.contact_phone}`"
              class="font-mono text-go4-primary hover:underline"
            >
              {{ selectedCall.contact_phone }}
            </a>
          </div>
          <div
            v-if="selectedCall.contact_email"
            class="flex items-center gap-2"
          >
            <svg
              class="h-4 w-4 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
              />
            </svg>
            <span class="text-sm text-gray-600 dark:text-gray-300">{{ selectedCall.contact_email }}</span>
          </div>
        </div>

        <!-- Call Script -->
        <div class="mt-6">
          <div class="flex items-center justify-between">
            <h4 class="text-sm font-medium text-gray-900 dark:text-gray-100">
              Gesprächsleitfaden
            </h4>
            <button
              type="button"
              class="text-sm text-go4-primary hover:underline disabled:opacity-50"
              :disabled="generatingScript === selectedCall.id"
              @click="handleGenerateScript(selectedCall)"
            >
              {{ generatingScript === selectedCall.id ? 'Generiere...' : selectedCall.suggested_content ? 'Neu generieren' : 'Generieren' }}
            </button>
          </div>
          <div
            v-if="selectedCall.suggested_content"
            class="mt-2 whitespace-pre-wrap rounded-lg bg-gray-50 p-4 text-sm text-gray-700 dark:bg-gray-900 dark:text-gray-300"
          >
            {{ selectedCall.suggested_content }}
          </div>
          <p
            v-else
            class="mt-2 text-sm italic text-gray-400 dark:text-gray-500"
          >
            Klicke "Generieren" um einen KI-Leitfaden zu erstellen.
          </p>
        </div>

        <!-- Action Buttons -->
        <div class="mt-6 flex gap-3">
          <button
            type="button"
            class="flex-1 rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark"
            @click="openLogModal(selectedCall)"
          >
            Anruf protokollieren
          </button>
        </div>
      </div>
    </div>

    <!-- Log Call Modal -->
    <div
      v-if="showLogModal"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      @click.self="showLogModal = false"
    >
      <div class="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800">
        <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Anruf protokollieren
        </h3>
        <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
          {{ selectedCall?.contact_name }} — {{ selectedCall?.contact_phone }}
        </p>

        <div class="mt-6 space-y-4">
          <!-- Outcome -->
          <div>
            <label class="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
              Ergebnis *
            </label>
            <div class="grid grid-cols-2 gap-2">
              <button
                v-for="opt in outcomeOptions"
                :key="opt.value"
                type="button"
                class="rounded-lg border px-3 py-2 text-left text-sm transition-colors"
                :class="
                  logForm.outcome === opt.value
                    ? 'border-go4-primary bg-go4-primary/10 text-go4-primary'
                    : 'border-gray-200 text-gray-700 hover:border-gray-300 dark:border-gray-600 dark:text-gray-300 dark:hover:border-gray-500'
                "
                @click="logForm.outcome = opt.value"
              >
                <span class="mr-1">{{ opt.icon }}</span> {{ opt.label }}
              </button>
            </div>
          </div>

          <!-- Duration -->
          <div>
            <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
              Dauer (Sekunden)
            </label>
            <input
              v-model.number="logForm.duration_seconds"
              type="number"
              min="0"
              placeholder="z.B. 120"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
            >
          </div>

          <!-- Notes -->
          <div>
            <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
              Notizen
            </label>
            <textarea
              v-model="logForm.notes"
              rows="3"
              placeholder="Gesprächsnotizen..."
              class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
            />
          </div>

          <!-- Follow-up Date -->
          <div v-if="logForm.outcome === 'callback'">
            <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
              Rückruf-Datum
            </label>
            <input
              v-model="logForm.follow_up_date"
              type="date"
              class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
            >
          </div>
        </div>

        <!-- Actions -->
        <div class="mt-6 flex justify-end gap-3">
          <button
            type="button"
            class="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
            @click="showLogModal = false"
          >
            Abbrechen
          </button>
          <button
            type="button"
            class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark disabled:opacity-50"
            :disabled="!logForm.outcome || loggingCall"
            @click="submitLog"
          >
            {{ loggingCall ? 'Speichere...' : 'Speichern' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
