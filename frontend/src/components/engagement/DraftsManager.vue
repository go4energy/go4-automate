<script setup>
/**
 * Drafts manager for the Aktionen-Tab in Pipeline-Detail.
 *
 * Lists all ready_for_approval pending_actions for a pipeline + channel,
 * with bulk-select, preview-modal, single + bulk regenerate, mass-replace
 * find/replace, and bulk-approve.
 */
import { ref, computed, onMounted, watch } from 'vue'
import {
  listDrafts,
  previewAction,
  bulkApproveActions,
  bulkRegenerateActions,
  regenerateAction,
  massReplaceInDrafts,
  bulkDeleteActions,
  deleteAllDrafts,
} from '@/api/engagement'

const props = defineProps({
  pipelineId: { type: Number, required: true },
})

const drafts = ref([])
const loading = ref(false)
const error = ref(null)
const channel = ref('email')
const selected = ref(new Set())

// Pagination + Filter
const pageSize = ref(20)
const page = ref(1)
const variantFilter = ref('')  // '', 'A', 'B', '-' (= unmarkiert)
const searchTerm = ref('')

const previewOpen = ref(false)
const previewLoading = ref(false)
const previewData = ref(null)

const massOpen = ref(false)
const massFind = ref('')
const massReplace = ref('')
const massBusy = ref(false)
const massResult = ref(null)

const regenBusy = ref(false)
const approveBusy = ref(false)
const deleteBusy = ref(false)

const stats = computed(() => {
  const total = drafts.value.length
  const stale = drafts.value.filter((d) => d.is_stale).length
  const sel = selected.value.size
  return { total, stale, sel }
})

const filtered = computed(() => {
  let rows = drafts.value
  if (variantFilter.value) {
    if (variantFilter.value === '-') {
      rows = rows.filter((d) => !d.ab_variant)
    } else {
      rows = rows.filter((d) => d.ab_variant === variantFilter.value)
    }
  }
  if (searchTerm.value.trim()) {
    const q = searchTerm.value.trim().toLowerCase()
    rows = rows.filter((d) =>
      [d.contact_name, d.company_name, d.subject, d.body_excerpt]
        .filter(Boolean)
        .some((s) => s.toLowerCase().includes(q)),
    )
  }
  return rows
})

const pageCount = computed(() => Math.max(1, Math.ceil(filtered.value.length / pageSize.value)))

const pageDrafts = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filtered.value.slice(start, start + pageSize.value)
})

watch([variantFilter, searchTerm, channel, pageSize], () => { page.value = 1 })

const variantCounts = computed(() => {
  const c = { A: 0, B: 0, none: 0 }
  for (const d of drafts.value) {
    if (d.ab_variant === 'A') c.A++
    else if (d.ab_variant === 'B') c.B++
    else c.none++
  }
  return c
})

const allSelected = computed(
  () => pageDrafts.value.length > 0 && pageDrafts.value.every((d) => selected.value.has(d.action_id)),
)

async function refresh() {
  loading.value = true
  error.value = null
  try {
    const { data } = await listDrafts(props.pipelineId, channel.value)
    drafts.value = data
    // Drop selections of disappeared rows
    const ids = new Set(data.map((d) => d.action_id))
    selected.value = new Set([...selected.value].filter((i) => ids.has(i)))
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    loading.value = false
  }
}

watch(channel, () => refresh())
onMounted(refresh)

function toggle(id) {
  const s = new Set(selected.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  selected.value = s
}

function toggleAll() {
  if (allSelected.value) {
    const ids = new Set(pageDrafts.value.map((d) => d.action_id))
    selected.value = new Set([...selected.value].filter((i) => !ids.has(i)))
  } else {
    const s = new Set(selected.value)
    for (const d of pageDrafts.value) s.add(d.action_id)
    selected.value = s
  }
}

function selectAllFiltered() {
  selected.value = new Set(filtered.value.map((d) => d.action_id))
}

function clearSelection() {
  selected.value = new Set()
}

async function openPreview(actionId) {
  previewOpen.value = true
  previewLoading.value = true
  previewData.value = null
  try {
    const { data } = await previewAction(actionId)
    previewData.value = data
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
    previewOpen.value = false
  } finally {
    previewLoading.value = false
  }
}

async function regenerate(actionId, modelOverride = null) {
  regenBusy.value = true
  try {
    await regenerateAction(actionId, modelOverride)
    await refresh()
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    regenBusy.value = false
  }
}

async function regenerateSelected() {
  if (!selected.value.size) return
  regenBusy.value = true
  try {
    await bulkRegenerateActions([...selected.value])
    await refresh()
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    regenBusy.value = false
  }
}

async function approveSelected() {
  if (!selected.value.size) return
  approveBusy.value = true
  try {
    const { data } = await bulkApproveActions([...selected.value])
    await refresh()
    error.value = `${data.approved} Drafts freigegeben — Worker sendet asynchron.`
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    approveBusy.value = false
  }
}

async function deleteOne(actionId) {
  if (!window.confirm('Diesen Draft endgültig löschen?')) return
  deleteBusy.value = true
  try {
    await bulkDeleteActions([actionId])
    selected.value.delete(actionId)
    await refresh()
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    deleteBusy.value = false
  }
}

async function deleteSelected() {
  if (!selected.value.size) return
  if (!window.confirm(`${selected.value.size} Drafts endgültig löschen?`)) return
  deleteBusy.value = true
  try {
    const { data } = await bulkDeleteActions([...selected.value])
    error.value = `${data.deleted} Drafts gelöscht.`
    selected.value = new Set()
    await refresh()
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    deleteBusy.value = false
  }
}

async function deleteAll() {
  const total = drafts.value.length
  if (!total) return
  if (!window.confirm(`ALLE ${total} Drafts dieser Pipeline (Channel ${channel.value}) endgültig löschen? Diese Aktion lässt sich nicht rückgängig machen.`)) return
  deleteBusy.value = true
  try {
    const { data } = await deleteAllDrafts(props.pipelineId, channel.value)
    error.value = `${data.deleted} Drafts gelöscht — bereit für neuen Bulk-Run.`
    selected.value = new Set()
    await refresh()
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    deleteBusy.value = false
  }
}

async function runMassReplace() {
  if (!massFind.value.trim()) return
  massBusy.value = true
  massResult.value = null
  try {
    const { data } = await massReplaceInDrafts(props.pipelineId, {
      find: massFind.value,
      replace: massReplace.value,
    })
    massResult.value = data
    await refresh()
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    massBusy.value = false
  }
}

function fmtDate(s) {
  if (!s) return ''
  try {
    return new Date(s).toLocaleString('de-DE')
  } catch {
    return s
  }
}
</script>

<template>
  <div class="space-y-4">
    <div class="rounded-lg bg-white p-5 shadow dark:bg-gray-800">
      <div class="mb-4 flex flex-wrap items-center gap-3">
        <select
          v-model="channel"
          class="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
        >
          <option value="email">✉ Email</option>
          <option value="letter">✉ Brief</option>
          <option value="linkedin">🔗 LinkedIn</option>
          <option value="whatsapp">💬 WhatsApp</option>
          <option value="phone">📞 Telefon</option>
        </select>
        <span class="text-sm text-gray-600 dark:text-gray-400">
          {{ stats.total }} Drafts
          <span v-if="stats.stale" class="text-amber-600 dark:text-amber-400">· {{ stats.stale }} veraltet</span>
          <span v-if="filtered.length !== stats.total" class="text-gray-400">· {{ filtered.length }} gefiltert</span>
        </span>
        <select
          v-model="variantFilter"
          class="rounded-md border border-gray-300 bg-white px-2 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
          title="A/B-Variante filtern"
        >
          <option value="">Alle Varianten</option>
          <option v-if="variantCounts.A" value="A">Nur Variante A ({{ variantCounts.A }})</option>
          <option v-if="variantCounts.B" value="B">Nur Variante B ({{ variantCounts.B }})</option>
          <option v-if="variantCounts.none" value="-">Ohne A/B-Tag ({{ variantCounts.none }})</option>
        </select>
        <input
          v-model="searchTerm"
          type="text"
          placeholder="Suche Name/Firma/Betreff…"
          class="rounded-md border border-gray-300 bg-white px-2 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
        />
        <span class="ml-auto flex flex-wrap gap-2">
          <button
            type="button"
            class="rounded-md border border-gray-300 px-3 py-2 text-xs font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700"
            @click="massOpen = true"
          >
            Find / Replace
          </button>
          <button
            type="button"
            class="rounded-md border border-gray-300 px-3 py-2 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700"
            :disabled="!stats.sel || regenBusy"
            @click="regenerateSelected"
          >
            {{ regenBusy ? 'Regeneriere…' : `Neu generieren (${stats.sel})` }}
          </button>
          <button
            type="button"
            class="rounded-md border border-red-300 px-3 py-2 text-xs font-medium text-red-700 hover:bg-red-50 disabled:opacity-50 dark:border-red-700 dark:text-red-300 dark:hover:bg-red-900/30"
            :disabled="!stats.sel || deleteBusy"
            @click="deleteSelected"
          >
            🗑 Löschen ({{ stats.sel }})
          </button>
          <button
            type="button"
            class="rounded-md border border-red-400 bg-red-50 px-3 py-2 text-xs font-medium text-red-800 hover:bg-red-100 disabled:opacity-50 dark:border-red-600 dark:bg-red-900/30 dark:text-red-300 dark:hover:bg-red-900/50"
            :disabled="!stats.total || deleteBusy"
            title="Alle Drafts dieses Channels löschen"
            @click="deleteAll"
          >
            ⚠ Alle löschen
          </button>
          <button
            type="button"
            class="rounded-md bg-emerald-600 px-3 py-2 text-xs font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
            :disabled="!stats.sel || approveBusy"
            @click="approveSelected"
          >
            {{ approveBusy ? 'Freigabe…' : `Freigeben + senden (${stats.sel})` }}
          </button>
        </span>
      </div>

      <div v-if="error" class="mb-3 rounded-md bg-amber-50 p-2 text-sm text-amber-800 dark:bg-amber-900/20 dark:text-amber-200">
        {{ error }}
      </div>

      <div v-if="loading" class="py-8 text-center text-sm text-gray-500">Lade Drafts…</div>
      <div v-else-if="!drafts.length" class="py-8 text-center text-sm text-gray-500">
        Keine offenen Drafts. Klicke „Brain durchlaufen lassen" auf der Übersicht, um welche zu erzeugen.
      </div>
      <table v-else class="w-full text-sm">
        <thead class="text-left text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
          <tr class="border-b border-gray-200 dark:border-gray-700">
            <th class="w-8 py-2">
              <input type="checkbox" :checked="allSelected" @change="toggleAll" />
            </th>
            <th class="py-2">Empfänger</th>
            <th class="py-2">Betreff</th>
            <th class="py-2">Eröffnung</th>
            <th class="py-2">Slot</th>
            <th class="py-2 w-32">Modell</th>
            <th class="py-2 w-32 text-right">Aktionen</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="d in pageDrafts"
            :key="d.action_id"
            class="border-b border-gray-100 hover:bg-gray-50 dark:border-gray-700/50 dark:hover:bg-gray-700/30"
            :class="d.is_stale ? 'bg-amber-50/50 dark:bg-amber-900/10' : ''"
          >
            <td class="py-2 align-top">
              <input
                type="checkbox"
                :checked="selected.has(d.action_id)"
                @change="toggle(d.action_id)"
              />
            </td>
            <td class="py-2 align-top">
              <div class="font-medium text-gray-900 dark:text-gray-100">{{ d.contact_name || '–' }}</div>
              <div class="text-xs text-gray-500 dark:text-gray-400">{{ d.company_name || '' }}</div>
            </td>
            <td class="py-2 align-top">
              <div class="line-clamp-2 text-gray-800 dark:text-gray-200">{{ d.subject || '(kein Betreff)' }}</div>
            </td>
            <td class="py-2 align-top">
              <div class="line-clamp-2 text-xs text-gray-600 dark:text-gray-400">{{ d.body_excerpt }}</div>
              <span
                v-if="d.is_stale"
                class="mt-1 inline-block rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-700 dark:bg-amber-900/40 dark:text-amber-300"
                :title="`Insights aktualisiert: ${fmtDate(d.insights_updated_at)}`"
              >
                ⚠ Insights neuer als Draft
              </span>
            </td>
            <td class="py-2 align-top">
              <span class="rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-mono text-gray-600 dark:bg-gray-700 dark:text-gray-300">
                {{ d.slot }}
              </span>
            </td>
            <td class="py-2 align-top">
              <div class="flex items-center gap-1">
                <span
                  v-if="d.ab_variant === 'A'"
                  class="rounded bg-blue-100 px-1.5 py-0.5 text-[10px] font-bold text-blue-700 dark:bg-blue-900/40 dark:text-blue-300"
                  title="A/B-Variante A"
                >A</span>
                <span
                  v-else-if="d.ab_variant === 'B'"
                  class="rounded bg-purple-100 px-1.5 py-0.5 text-[10px] font-bold text-purple-700 dark:bg-purple-900/40 dark:text-purple-300"
                  title="A/B-Variante B"
                >B</span>
                <span class="text-[10px] font-mono text-gray-500 dark:text-gray-400">{{ d.model_used || '—' }}</span>
              </div>
            </td>
            <td class="py-2 align-top text-right">
              <button
                type="button"
                class="rounded p-1 text-gray-400 transition hover:bg-gray-100 hover:text-go4-primary dark:hover:bg-gray-700"
                title="Vorschau"
                @click="openPreview(d.action_id)"
              >
                👁
              </button>
              <button
                type="button"
                class="ml-1 rounded p-1 text-gray-400 transition hover:bg-gray-100 hover:text-go4-primary disabled:opacity-30 dark:hover:bg-gray-700"
                title="Neu generieren"
                :disabled="regenBusy"
                @click="regenerate(d.action_id)"
              >
                🔄
              </button>
              <button
                type="button"
                class="ml-1 rounded p-1 text-gray-400 transition hover:bg-red-100 hover:text-red-600 disabled:opacity-30 dark:hover:bg-red-900/30"
                title="Löschen"
                :disabled="deleteBusy"
                @click="deleteOne(d.action_id)"
              >
                🗑
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Pagination footer -->
      <div v-if="filtered.length > 0" class="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm text-gray-600 dark:text-gray-400">
        <div class="flex items-center gap-2">
          <span>Pro Seite:</span>
          <select
            v-model.number="pageSize"
            class="rounded border border-gray-300 bg-white px-2 py-1 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
          >
            <option :value="20">20</option>
            <option :value="50">50</option>
            <option :value="100">100</option>
          </select>
          <span class="text-xs">
            Zeige {{ (page - 1) * pageSize + 1 }}–{{ Math.min(page * pageSize, filtered.length) }} von {{ filtered.length }}
          </span>
        </div>
        <div class="flex items-center gap-2">
          <button
            type="button"
            class="rounded border border-gray-300 px-2 py-1 text-xs disabled:opacity-30 dark:border-gray-600"
            :disabled="page <= 1"
            @click="page = 1"
          >« Erste</button>
          <button
            type="button"
            class="rounded border border-gray-300 px-2 py-1 text-xs disabled:opacity-30 dark:border-gray-600"
            :disabled="page <= 1"
            @click="page--"
          >‹ Zurück</button>
          <span class="px-2 text-xs">Seite {{ page }} / {{ pageCount }}</span>
          <button
            type="button"
            class="rounded border border-gray-300 px-2 py-1 text-xs disabled:opacity-30 dark:border-gray-600"
            :disabled="page >= pageCount"
            @click="page++"
          >Weiter ›</button>
          <button
            type="button"
            class="rounded border border-gray-300 px-2 py-1 text-xs disabled:opacity-30 dark:border-gray-600"
            :disabled="page >= pageCount"
            @click="page = pageCount"
          >Letzte »</button>
        </div>
        <div class="flex items-center gap-2">
          <button
            type="button"
            class="rounded border border-gray-300 px-2 py-1 text-xs hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-700"
            @click="selectAllFiltered"
          >Alle {{ filtered.length }} markieren</button>
          <button
            v-if="stats.sel > 0"
            type="button"
            class="rounded border border-gray-300 px-2 py-1 text-xs hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-700"
            @click="clearSelection"
          >Auswahl leeren ({{ stats.sel }})</button>
        </div>
      </div>
    </div>

    <!-- Preview Modal -->
    <div
      v-if="previewOpen"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      @click.self="previewOpen = false"
    >
      <div class="flex h-[90vh] w-full max-w-4xl flex-col rounded-lg bg-white shadow-2xl dark:bg-gray-800">
        <header class="flex items-center justify-between border-b border-gray-200 px-5 py-3 dark:border-gray-700">
          <div>
            <p class="text-xs text-gray-500 dark:text-gray-400">Vorschau Email</p>
            <p class="text-base font-semibold text-gray-900 dark:text-gray-100">
              {{ previewData?.subject || '…' }}
            </p>
            <p class="text-xs text-gray-500 dark:text-gray-400">
              {{ previewData?.contact_name }} · {{ previewData?.contact_email }}
              <span v-if="previewData?.is_stale" class="ml-2 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-700">⚠ Veraltet</span>
            </p>
          </div>
          <button
            type="button"
            class="rounded p-1.5 text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700"
            @click="previewOpen = false"
          >
            ✕
          </button>
        </header>
        <div class="flex-1 overflow-auto bg-gray-50 p-4 dark:bg-gray-900">
          <div v-if="previewLoading" class="py-12 text-center text-sm text-gray-500">Lade Vorschau…</div>
          <div v-else-if="previewData" class="mx-auto max-w-2xl rounded bg-white p-6 shadow dark:bg-gray-800">
            <div v-html="previewData.html" />
          </div>
        </div>
      </div>
    </div>

    <!-- Mass-Replace Modal -->
    <div
      v-if="massOpen"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      @click.self="massOpen = false"
    >
      <div class="w-full max-w-md rounded-lg bg-white p-5 shadow-xl dark:bg-gray-800">
        <h3 class="mb-3 text-base font-semibold text-gray-900 dark:text-gray-100">Find / Replace über alle Drafts</h3>
        <p class="mb-3 text-xs text-gray-600 dark:text-gray-400">
          Ersetzt buchstabengenau in <strong>Subject + Eröffnung</strong> aller offenen Drafts dieser Pipeline.
        </p>
        <label class="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">Suchen</label>
        <input
          v-model="massFind"
          class="mb-3 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
        />
        <label class="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">Ersetzen durch</label>
        <input
          v-model="massReplace"
          class="mb-3 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
        />
        <div v-if="massResult" class="mb-3 rounded-md bg-emerald-50 p-2 text-xs text-emerald-800 dark:bg-emerald-900/20 dark:text-emerald-200">
          {{ massResult.changed }} von {{ massResult.matched }} Drafts angepasst.
        </div>
        <div class="flex justify-end gap-2">
          <button
            type="button"
            class="rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700"
            @click="massOpen = false"
          >
            Schließen
          </button>
          <button
            type="button"
            class="rounded-md bg-go4-primary px-3 py-1.5 text-sm font-medium text-white hover:bg-go4-primary-dark disabled:opacity-50"
            :disabled="!massFind.trim() || massBusy"
            @click="runMassReplace"
          >
            {{ massBusy ? 'Läuft…' : 'Ersetzen' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
