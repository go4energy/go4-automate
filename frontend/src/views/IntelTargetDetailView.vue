<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useIntelStore } from '@/stores/intel'
import PageHeader from '@/components/ui/PageHeader.vue'

const props = defineProps({ id: { type: [String, Number], default: null } })
const route = useRoute()
const store = useIntelStore()

const targetId = computed(() => Number(props.id || route.params.id))
const target = ref(null)
const sources = computed(() => store.sources[targetId.value] || [])

const showAdd = ref(false)
const newSource = ref({ adapter: 'web', url: '', fetch_interval_sec: 3600 })

onMounted(async () => {
  await store.fetchTargets()
  target.value = store.targets.find((t) => t.id === targetId.value)
  await store.fetchSources(targetId.value)
})

async function addSource() {
  if (!newSource.value.url.trim()) return
  await store.createSource(targetId.value, {
    adapter: newSource.value.adapter,
    config: { url: newSource.value.url.trim() },
    fetch_interval_sec: Number(newSource.value.fetch_interval_sec) || 3600,
    is_active: true
  })
  newSource.value = { adapter: 'web', url: '', fetch_interval_sec: 3600 }
  showAdd.value = false
  await store.fetchSources(targetId.value)
}

async function removeSource(s) {
  if (!confirm(`Source "${s.config?.url || s.id}" löschen?`)) return
  await store.deleteSource(s.id)
  await store.fetchSources(targetId.value)
}

const statusBadge = {
  ok: 'bg-emerald-100 text-emerald-800',
  failed: 'bg-red-100 text-red-800',
  pending: 'bg-gray-100 text-gray-600'
}
</script>

<template>
  <div>
    <PageHeader :title="target ? target.name : 'Target'" info-module="intel" />

    <div v-if="!target" class="text-sm text-go4-muted dark:text-gray-400">
      Lade Target…
    </div>
    <div v-else>
      <div class="mb-6 rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
        <dl class="grid grid-cols-2 gap-4 text-sm md:grid-cols-3">
          <div>
            <dt class="text-go4-muted dark:text-gray-400">Name</dt>
            <dd class="font-medium text-go4-secondary dark:text-gray-100">{{ target.name }}</dd>
          </div>
          <div>
            <dt class="text-go4-muted dark:text-gray-400">Typ</dt>
            <dd class="font-medium text-go4-secondary dark:text-gray-100">{{ target.kind }}</dd>
          </div>
          <div>
            <dt class="text-go4-muted dark:text-gray-400">Status</dt>
            <dd class="font-medium text-go4-secondary dark:text-gray-100">
              {{ target.is_active ? 'Aktiv' : 'Inaktiv' }}
            </dd>
          </div>
        </dl>
      </div>

      <div class="mb-4 flex items-center justify-between">
        <h3 class="text-lg font-semibold text-go4-secondary dark:text-white">
          Sources ({{ sources.length }})
        </h3>
        <button
          type="button"
          class="rounded-lg bg-go4-primary px-3 py-1.5 text-sm font-medium text-white hover:bg-go4-primary-dark"
          @click="showAdd = !showAdd"
        >
          {{ showAdd ? '× Abbrechen' : '+ Source' }}
        </button>
      </div>

      <div
        v-if="showAdd"
        class="mb-4 rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
      >
        <div class="grid gap-3 sm:grid-cols-[180px_1fr_180px]">
          <select
            v-model="newSource.adapter"
            class="rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
          >
            <option value="web">Web (statisch)</option>
            <option value="web_js">Web (JS-Rendering)</option>
            <option value="rss">RSS / Atom</option>
          </select>
          <input
            v-model="newSource.url"
            type="url"
            placeholder="https://…"
            class="rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
          >
          <input
            v-model.number="newSource.fetch_interval_sec"
            type="number"
            min="300"
            max="86400"
            class="rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            placeholder="Intervall (s)"
          >
        </div>
        <div class="mt-3 flex justify-end">
          <button
            type="button"
            class="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700"
            @click="addSource"
          >
            Anlegen
          </button>
        </div>
      </div>

      <div
        v-if="sources.length === 0"
        class="rounded-lg border-2 border-dashed border-gray-200 p-8 text-center text-sm text-go4-muted dark:border-gray-700 dark:text-gray-400"
      >
        Noch keine Sources.
      </div>
      <ul v-else class="space-y-2">
        <li
          v-for="s in sources"
          :key="s.id"
          class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
        >
          <div class="flex items-start justify-between gap-4">
            <div class="min-w-0 flex-1">
              <p class="truncate text-sm font-medium text-go4-secondary dark:text-gray-100">
                {{ s.config?.url || '(kein URL)' }}
              </p>
              <p class="mt-1 text-xs text-go4-muted">
                Adapter: <strong>{{ s.adapter }}</strong> · Intervall: {{ s.fetch_interval_sec }}s
                <span v-if="s.last_fetched_at">
                  · Zuletzt: {{ new Date(s.last_fetched_at).toLocaleString('de-DE') }}
                </span>
              </p>
              <p v-if="s.last_error" class="mt-1 truncate text-xs text-red-600">{{ s.last_error }}</p>
            </div>
            <div class="flex flex-col items-end gap-1">
              <span
                class="rounded px-2 py-0.5 text-[10px] font-medium uppercase"
                :class="statusBadge[s.last_status] || statusBadge.pending"
              >
                {{ s.last_status }}
              </span>
              <button
                type="button"
                class="text-xs text-red-500 hover:text-red-700"
                @click="removeSource(s)"
              >
                Entfernen
              </button>
            </div>
          </div>
        </li>
      </ul>
    </div>
  </div>
</template>
