<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useIntelStore } from '@/stores/intel'
import PageHeader from '@/components/ui/PageHeader.vue'

const route = useRoute()
const router = useRouter()
const store = useIntelStore()

const tabs = [
  { key: 'dashboard', label: 'Dashboard', route: '/intel' },
  { key: 'targets', label: 'Targets', route: '/intel/targets' },
  { key: 'briefings', label: 'Briefings', route: '/intel/briefings' },
  { key: 'events', label: 'Events', route: '/intel/events' }
]
const activeTab = computed(() => route.meta?.tab || 'dashboard')

const embedHealthy = ref(null)
const embedBackend = ref('ollama')
const triggering = ref(false)

onMounted(async () => {
  await Promise.all([store.fetchTargets(), store.fetchBriefings({ limit: 5 })])
  try {
    const status = await store.probeEmbedding()
    embedHealthy.value = status?.healthy
    embedBackend.value = status?.backend || 'ollama'
  } catch {
    embedHealthy.value = false
  }
})

const stats = computed(() => {
  const total = store.targets.length
  const active = store.targets.filter((t) => t.is_active).length
  const briefings = store.briefings.length
  return { total, active, briefings }
})

async function triggerNow() {
  triggering.value = true
  try {
    await store.runNow()
    await store.fetchBriefings({ limit: 5 })
  } finally {
    triggering.value = false
  }
}
</script>

<template>
  <div>
    <PageHeader title="Intel" info-module="intel">
      <template #actions>
        <button
          type="button"
          class="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
          :disabled="triggering"
          @click="triggerNow"
        >
          {{ triggering ? 'Läuft…' : 'Jetzt prüfen' }}
        </button>
      </template>
    </PageHeader>

    <nav class="mb-6 border-b border-gray-200 dark:border-gray-700">
      <div class="-mb-px flex gap-6">
        <router-link
          v-for="t in tabs"
          :key="t.key"
          :to="t.route"
          class="border-b-2 pb-3 text-sm font-medium transition"
          :class="
            activeTab === t.key
              ? 'border-go4-primary text-go4-primary'
              : 'border-transparent text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200'
          "
        >
          {{ t.label }}
        </router-link>
      </div>
    </nav>

    <!-- KPIs -->
    <div class="mb-6 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
      <div class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
        <p class="text-sm text-go4-muted dark:text-gray-400">Aktive Targets</p>
        <p class="mt-1 text-2xl font-semibold text-go4-secondary dark:text-white">
          {{ stats.active }}<span class="text-base font-normal text-gray-400"> / {{ stats.total }}</span>
        </p>
      </div>
      <div class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
        <p class="text-sm text-go4-muted dark:text-gray-400">Briefings (letzte)</p>
        <p class="mt-1 text-2xl font-semibold text-go4-secondary dark:text-white">
          {{ stats.briefings }}
        </p>
      </div>
      <div class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
        <p class="text-sm text-go4-muted dark:text-gray-400">
          Embeddings ({{ embedBackend }})
        </p>
        <p class="mt-2 text-sm font-medium">
          <span
            v-if="embedHealthy === true"
            class="inline-flex items-center gap-2 text-emerald-600"
          >
            <span class="h-2 w-2 rounded-full bg-emerald-500" />
            Online
          </span>
          <span
            v-else-if="embedHealthy === false"
            class="inline-flex items-center gap-2 text-red-600"
          >
            <span class="h-2 w-2 rounded-full bg-red-500" />
            Offline
          </span>
          <span v-else class="text-gray-400">…</span>
        </p>
      </div>
      <div class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
        <p class="text-sm text-go4-muted dark:text-gray-400">Quellen-Status</p>
        <p class="mt-2 text-sm text-gray-500 dark:text-gray-400">
          Worker prüft alle Sources im konfigurierten Intervall.
        </p>
      </div>
    </div>

    <!-- Recent briefings -->
    <div class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
      <h3 class="mb-4 text-lg font-semibold text-go4-secondary dark:text-white">Letzte Briefings</h3>
      <div v-if="store.briefings.length === 0" class="text-sm text-go4-muted dark:text-gray-400">
        Noch keine Briefings vorhanden. Sobald du Targets + Sources angelegt hast,
        erzeugt der Worker täglich ein neues Briefing.
      </div>
      <ul v-else class="divide-y divide-gray-100 dark:divide-gray-700">
        <li
          v-for="b in store.briefings"
          :key="b.id"
          class="cursor-pointer py-3 hover:bg-gray-50 dark:hover:bg-gray-700/50"
          @click="router.push(`/intel/briefings/${b.id}`)"
        >
          <p class="text-sm font-medium text-gray-900 dark:text-gray-100">
            {{ new Date(b.period_end).toLocaleDateString('de-DE') }} —
            {{ (b.payload?.sections || []).length }} Sektionen
          </p>
          <p class="truncate text-xs text-gray-500 dark:text-gray-400">
            {{ b.tts_summary }}
          </p>
        </li>
      </ul>
    </div>
  </div>
</template>
