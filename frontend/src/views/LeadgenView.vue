<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useLeadgenStore } from '@/stores/leadgen'
import PageHeader from '@/components/ui/PageHeader.vue'
import EmptyState from '@/components/ui/EmptyState.vue'

const router = useRouter()
const store = useLeadgenStore()

const filterText = ref('')
// Delete-confirmation requires typing the campaign's exact name. Cheap
// safety-belt against accidental clicks since "Löschen" cascades to runs +
// places and there is no undo.
const showDeleteConfirm = ref(false)
const campaignToDelete = ref(null)
const deleteTypedName = ref('')
const deleteWorking = ref(false)
const deleteError = ref(null)
const deleteNameMatches = computed(
  () =>
    !!campaignToDelete.value &&
    deleteTypedName.value === campaignToDelete.value.name
)

const POLL_INTERVAL_MS = 4000
let pollTimer = null

onMounted(async () => {
  await store.fetchCampaigns()
  startPolling()
})

onBeforeUnmount(() => {
  stopPolling()
})

function hasLiveRun() {
  return (store.campaigns || []).some((c) => c.active_run)
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(async () => {
    if (!hasLiveRun()) return
    try {
      await store.fetchCampaigns()
    } catch {
      // swallow polling errors so we keep trying
    }
  }, POLL_INTERVAL_MS)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

const filteredCampaigns = computed(() => {
  if (!filterText.value) return store.campaigns
  const q = filterText.value.toLowerCase()
  return store.campaigns.filter(
    (c) =>
      c.name.toLowerCase().includes(q) ||
      c.slug.toLowerCase().includes(q) ||
      (c.description || '').toLowerCase().includes(q)
  )
})

function statusBadgeClass(status) {
  const base = 'inline-flex px-2 py-0.5 text-xs font-medium rounded'
  switch (status) {
    case 'draft':
      return `${base} bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-200`
    case 'active':
      return `${base} bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200`
    case 'paused':
      return `${base} bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-200`
    case 'completed':
      return `${base} bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200`
    default:
      return `${base} bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-200`
  }
}

function runStageLabel(run) {
  if (!run) return null
  const stage = run.current_stage
  const stageMap = {
    places: 'Discovery',
    impressum: 'Impressum',
    impressum_pending: 'Impressum (wartet)',
    llm: 'LLM-Analyse',
    llm_pending: 'LLM (wartet)',
    completed: 'Abgeschlossen'
  }
  return stageMap[stage] || stage
}

function runProgressPct(run) {
  if (!run || !run.total) return null
  return Math.min(100, Math.round((run.processed / run.total) * 100))
}

function formatDate(d) {
  if (!d) return '-'
  return new Date(d).toLocaleString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function openCampaign(c) {
  router.push(`/leadgen/campaigns/${c.id}/details`)
}

function openEdit(c) {
  router.push(`/leadgen/campaigns/${c.id}/edit`)
}

function askDelete(c) {
  campaignToDelete.value = c
  deleteTypedName.value = ''
  deleteError.value = null
  deleteWorking.value = false
  showDeleteConfirm.value = true
}

function cancelDelete() {
  if (deleteWorking.value) return
  showDeleteConfirm.value = false
  campaignToDelete.value = null
  deleteTypedName.value = ''
  deleteError.value = null
}

async function confirmDelete() {
  if (!campaignToDelete.value || !deleteNameMatches.value) return
  deleteWorking.value = true
  deleteError.value = null
  try {
    await store.removeCampaign(campaignToDelete.value.id)
    cancelDelete()
  } catch (e) {
    deleteError.value = e.response?.data?.detail || e.message || 'Löschen fehlgeschlagen'
  } finally {
    deleteWorking.value = false
  }
}
</script>

<template>
  <div class="space-y-4">
    <PageHeader
      title="Leadgen"
      subtitle="B2B-Lead-Discovery und Anreicherung"
    />

    <div
      v-if="store.error"
      class="rounded-lg bg-red-50 p-3 text-sm text-red-700"
    >
      {{ store.error }}
    </div>

    <!-- Filter + Aktionen -->
    <div class="flex items-center justify-between gap-3">
      <input
        v-model="filterText"
        type="text"
        placeholder="Kampagne filtern…"
        class="w-72 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800"
      >
      <router-link
        to="/leadgen/campaigns/new"
        class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary/90"
      >
        + Neue Kampagne
      </router-link>
    </div>

    <!-- Empty -->
    <EmptyState
      v-if="store.campaigns.length === 0 && !store.loading"
      title="Noch keine Kampagne"
    />

    <!-- Tabelle -->
    <div
      v-else
      class="overflow-hidden rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800"
    >
      <table class="w-full text-sm">
        <thead class="bg-gray-50 text-left text-xs uppercase tracking-wide text-gray-600 dark:bg-gray-900/40 dark:text-gray-300">
          <tr>
            <th class="px-4 py-2">
              Kampagne
            </th>
            <th class="px-4 py-2">
              Status
            </th>
            <th class="px-4 py-2 text-right">
              Leads
            </th>
            <th class="px-4 py-2 text-right">
              Angereichert
            </th>
            <th class="px-4 py-2">
              Aktiver Prozess
            </th>
            <th class="px-4 py-2">
              Aktualisiert
            </th>
            <th class="px-4 py-2 text-right">
              Aktionen
            </th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
          <tr
            v-for="c in filteredCampaigns"
            :key="c.id"
            class="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/40"
            @click="openCampaign(c)"
          >
            <td class="px-4 py-3">
              <div class="font-medium text-gray-900 dark:text-gray-100">
                {{ c.name }}
              </div>
              <div class="text-xs text-gray-500">
                {{ c.slug }}
              </div>
            </td>
            <td class="px-4 py-3">
              <span :class="statusBadgeClass(c.status)">{{ c.status }}</span>
            </td>
            <td class="px-4 py-3 text-right tabular-nums">
              {{ (c.total_places || 0).toLocaleString('de-DE') }}
            </td>
            <td class="px-4 py-3 text-right tabular-nums">
              <span v-if="c.total_places">
                {{ (c.enriched_places || 0).toLocaleString('de-DE') }}
                <span class="text-xs text-gray-500">
                  ({{ Math.round((c.enriched_places / c.total_places) * 100) }}%)
                </span>
              </span>
              <span
                v-else
                class="text-gray-400"
              >—</span>
            </td>
            <td class="px-4 py-3">
              <div
                v-if="c.active_run"
                class="space-y-1"
              >
                <div class="text-xs">
                  <span class="font-mono text-gray-500">#{{ c.active_run.id }}</span>
                  <span class="ml-1 font-medium">{{ runStageLabel(c.active_run) }}</span>
                  <span
                    class="ml-1 rounded-full px-1.5 py-0.5 text-[10px]"
                    :class="c.active_run.status === 'running' ? 'bg-green-100 text-green-800 animate-pulse dark:bg-green-900/40 dark:text-green-200' : c.active_run.status === 'paused' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-200' : 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200'"
                  >
                    {{ c.active_run.status }}
                  </span>
                </div>
                <div
                  v-if="runProgressPct(c.active_run) !== null"
                  class="text-xs text-gray-500"
                >
                  {{ c.active_run.processed.toLocaleString('de-DE') }} /
                  {{ c.active_run.total.toLocaleString('de-DE') }}
                  · {{ runProgressPct(c.active_run) }}%
                </div>
                <div
                  v-if="runProgressPct(c.active_run) !== null"
                  class="h-1 w-32 rounded-full bg-gray-200 dark:bg-gray-700"
                >
                  <div
                    class="h-1 rounded-full bg-go4-primary transition-all"
                    :style="{ width: runProgressPct(c.active_run) + '%' }"
                  />
                </div>
              </div>
              <span
                v-else
                class="text-xs text-gray-400"
              >—</span>
            </td>
            <td class="px-4 py-3 text-xs text-gray-500">
              {{ formatDate(c.updated_at) }}
            </td>
            <td
              class="px-4 py-3 text-right"
              @click.stop
            >
              <button
                class="rounded-lg border border-gray-300 px-2.5 py-1 text-xs hover:bg-gray-100 dark:border-gray-600 dark:hover:bg-gray-700"
                @click="openEdit(c)"
              >
                Bearbeiten
              </button>
              <button
                class="ml-1 rounded-lg border border-red-200 px-2.5 py-1 text-xs text-red-600 hover:bg-red-50 dark:border-red-800 dark:hover:bg-red-900/30"
                @click="askDelete(c)"
              >
                Löschen
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Type-the-name delete confirmation. Generic ConfirmDialog isn't
         enough here because the cascade (runs, places, insights) is
         destructive and one-click. Forcing the operator to retype the exact
         name is the standard GitHub-pattern safety-belt. -->
    <div
      v-if="showDeleteConfirm"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      @click.self="cancelDelete"
    >
      <div class="w-full max-w-md rounded-xl bg-white p-6 shadow-xl dark:bg-gray-800">
        <h3 class="text-lg font-semibold text-red-700 dark:text-red-400">
          Kampagne unwiderruflich löschen
        </h3>
        <p class="mt-2 text-sm text-gray-700 dark:text-gray-300">
          Du bist dabei,
          <code class="rounded bg-red-50 px-1 py-0.5 font-mono text-red-700 dark:bg-red-900/40 dark:text-red-200">{{ campaignToDelete?.name }}</code>
          inklusive aller Runs und Stats zu löschen.
        </p>
        <p class="mt-2 rounded-lg bg-amber-50 p-2 text-xs text-amber-800 dark:bg-amber-900/30 dark:text-amber-200">
          Tippe zur Bestätigung den exakten Kampagnen-Namen ein. Diese Aktion
          kann nicht rückgängig gemacht werden.
        </p>

        <label class="mt-4 block text-sm">
          <span class="text-gray-700 dark:text-gray-300">Kampagnen-Name</span>
          <input
            v-model="deleteTypedName"
            type="text"
            :placeholder="campaignToDelete?.name || ''"
            autocomplete="off"
            class="mt-1 w-full rounded-lg border px-3 py-2 font-mono text-sm dark:bg-gray-900"
            :class="
              deleteNameMatches
                ? 'border-green-400 ring-1 ring-green-400 dark:border-green-600'
                : 'border-gray-300 dark:border-gray-600'
            "
            @keyup.enter="deleteNameMatches && confirmDelete()"
          >
        </label>

        <p
          v-if="deleteError"
          class="mt-3 rounded-lg bg-red-50 p-2 text-sm text-red-700 dark:bg-red-900/40 dark:text-red-200"
        >
          {{ deleteError }}
        </p>

        <div class="mt-5 flex justify-end gap-2">
          <button
            class="rounded-lg border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-700"
            :disabled="deleteWorking"
            @click="cancelDelete"
          >
            Abbrechen
          </button>
          <button
            class="rounded-lg bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-40 disabled:cursor-not-allowed"
            :disabled="!deleteNameMatches || deleteWorking"
            @click="confirmDelete"
          >
            {{ deleteWorking ? 'Lösche…' : 'Endgültig löschen' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
