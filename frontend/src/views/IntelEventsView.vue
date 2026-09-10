<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useIntelStore } from '@/stores/intel'
import PageHeader from '@/components/ui/PageHeader.vue'

const route = useRoute()
const store = useIntelStore()

const tabs = [
  { key: 'dashboard', label: 'Dashboard', route: '/intel' },
  { key: 'targets', label: 'Targets', route: '/intel/targets' },
  { key: 'briefings', label: 'Briefings', route: '/intel/briefings' },
  { key: 'events', label: 'Events', route: '/intel/events' }
]
const activeTab = computed(() => route.meta?.tab || 'events')

const minSig = ref(0.3)

async function load() {
  await store.fetchEvents({ min_significance: minSig.value, limit: 100 })
}

onMounted(load)

const sigBar = (v) => {
  const pct = Math.round((v || 0) * 100)
  if (pct >= 70) return ['bg-red-500', `${pct}%`]
  if (pct >= 40) return ['bg-amber-500', `${pct}%`]
  return ['bg-gray-400', `${pct}%`]
}
</script>

<template>
  <div>
    <PageHeader title="Intel" info-module="intel" />

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

    <div class="mb-4 flex items-center gap-3">
      <label class="text-sm text-go4-muted dark:text-gray-300">
        Min. Bedeutung:
        <input
          v-model.number="minSig"
          type="range"
          min="0"
          max="1"
          step="0.1"
          class="mx-2 align-middle"
          @change="load"
        >
        {{ Math.round(minSig * 100) }}%
      </label>
    </div>

    <div
      v-if="store.events.length === 0"
      class="rounded-lg border-2 border-dashed border-gray-200 p-12 text-center text-sm text-go4-muted dark:border-gray-700 dark:text-gray-400"
    >
      Keine Events oberhalb des Schwellenwerts.
    </div>
    <ul v-else class="space-y-2">
      <li
        v-for="e in store.events"
        :key="e.id"
        class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
      >
        <div class="flex items-start justify-between gap-4">
          <div class="min-w-0 flex-1">
            <p class="text-sm font-medium text-go4-secondary dark:text-gray-100">
              {{ e.headline || '(noch unbenannt)' }}
            </p>
            <p class="mt-1 text-xs text-go4-muted">
              <strong>{{ e.change_type }}</strong> ·
              {{ new Date(e.created_at).toLocaleString('de-DE') }}
            </p>
            <p v-if="e.summary" class="mt-2 text-sm text-gray-600 dark:text-gray-300">
              {{ e.summary }}
            </p>
          </div>
          <div class="w-32 shrink-0">
            <div class="h-1.5 w-full overflow-hidden rounded-full bg-gray-200">
              <div
                class="h-full rounded-full"
                :class="sigBar(e.significance)[0]"
                :style="{ width: sigBar(e.significance)[1] }"
              />
            </div>
            <p class="mt-1 text-right text-xs text-gray-500">
              {{ Math.round((e.significance || 0) * 100) }}%
            </p>
          </div>
        </div>
      </li>
    </ul>
  </div>
</template>
