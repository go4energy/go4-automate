<script setup>
/**
 * Single source of truth for "campaigns" across the platform.
 *
 * Engagement-Pipelines == Kampagnen. Each outreach module (LinkedIn,
 * Email, Letter, WhatsApp) renders this component with `channelFilter`
 * set to its channel; the user then sees the same list of pipelines
 * the engagement module shows, but filtered to the relevant ones.
 *
 * Click on a pipeline → jumps to the central engagement pipeline detail
 * view, so all per-pipeline data (Enrollments, Aktionen, Aktivitäten,
 * AB-Tests) lives in one place regardless of which module the user
 * came from.
 */

import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useEngagementStore } from '@/stores/engagement'

const props = defineProps({
  channelFilter: { type: String, default: null }, // null = no filter
  emptyHint: { type: String, default: '' },
})

const router = useRouter()
const store = useEngagementStore()

const loading = ref(false)
const error = ref(null)

const channelLabels = {
  linkedin: 'LinkedIn',
  email: 'Email',
  letter: 'Brief',
  phone: 'Telefon',
  whatsapp: 'WhatsApp',
}

const filteredPipelines = computed(() => {
  if (!props.channelFilter) return store.pipelines
  return (store.pipelines || []).filter((p) =>
    (p.channels || []).includes(props.channelFilter)
  )
})

const totalEngagementPipelines = computed(() => store.pipelines?.length || 0)

async function load() {
  loading.value = true
  error.value = null
  try {
    await store.fetchPipelines()
  } catch (err) {
    error.value = err.response?.data?.detail || err.message
  } finally {
    loading.value = false
  }
}

function openPipeline(p) {
  router.push(`/engagement/pipelines/${p.id}/uebersicht`)
}

function newPipeline() {
  router.push('/engagement/pipelines/new')
}

onMounted(load)
</script>

<template>
  <div class="space-y-4">
    <!-- Header / actions -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Kampagnen
        </h2>
        <p class="text-sm text-gray-500 dark:text-gray-400">
          <span v-if="channelFilter">
            Engagement-Pipelines mit Kanal
            <strong>{{ channelLabels[channelFilter] || channelFilter }}</strong>
            ({{ filteredPipelines.length }} von {{ totalEngagementPipelines }})
          </span>
          <span v-else>
            Alle Engagement-Pipelines ({{ totalEngagementPipelines }})
          </span>
        </p>
      </div>
      <button
        type="button"
        class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark"
        @click="newPipeline"
      >
        + Neue Kampagne
      </button>
    </div>

    <!-- States -->
    <div
      v-if="loading"
      class="py-8 text-center text-gray-500"
    >
      Laden...
    </div>
    <div
      v-else-if="error"
      class="rounded-lg bg-red-50 p-4 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-300"
    >
      {{ error }}
    </div>
    <div
      v-else-if="filteredPipelines.length === 0"
      class="rounded-lg border border-dashed border-gray-300 bg-white p-8 text-center text-sm text-gray-500 dark:border-gray-600 dark:bg-gray-800"
    >
      <p class="font-medium text-gray-700 dark:text-gray-300">
        Keine Kampagnen
      </p>
      <p
        v-if="emptyHint"
        class="mt-1"
      >
        {{ emptyHint }}
      </p>
      <p
        v-else-if="channelFilter"
        class="mt-1"
      >
        Keine Engagement-Pipeline nutzt aktuell den Kanal
        <strong>{{ channelLabels[channelFilter] || channelFilter }}</strong>.
        Beim Anlegen einer neuen Pipeline diesen Kanal aktivieren.
      </p>
    </div>

    <!-- List -->
    <div
      v-else
      class="grid grid-cols-1 gap-3 lg:grid-cols-2"
    >
      <button
        v-for="p in filteredPipelines"
        :key="p.id"
        type="button"
        class="rounded-lg border border-gray-200 bg-white p-4 text-left shadow-sm transition hover:border-go4-primary hover:shadow-md dark:border-gray-700 dark:bg-gray-800 dark:hover:border-go4-primary"
        @click="openPipeline(p)"
      >
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0 flex-1">
            <div class="font-semibold text-gray-900 dark:text-gray-100">
              {{ p.name }}
            </div>
            <div class="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
              {{ p.product_name || p.slug }}
            </div>
          </div>
          <span
            class="rounded px-2 py-0.5 text-[10px] font-medium uppercase"
            :class="p.is_active ? 'bg-emerald-100 text-emerald-800' : 'bg-gray-100 text-gray-600'"
          >
            {{ p.is_active ? 'aktiv' : 'inaktiv' }}
          </span>
        </div>

        <div class="mt-3 flex flex-wrap gap-1">
          <span
            v-for="ch in p.channels"
            :key="ch"
            class="inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium"
            :class="
              ch === channelFilter
                ? 'bg-go4-primary/10 text-go4-primary ring-1 ring-go4-primary/30'
                : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
            "
          >
            {{ channelLabels[ch] || ch }}
          </span>
        </div>

        <div class="mt-3 grid grid-cols-2 gap-2 text-xs text-gray-500 dark:text-gray-400">
          <div>
            <span class="font-medium text-gray-700 dark:text-gray-300">{{ p.active_enrollment_count ?? 0 }}</span>
            aktiv enrolled
          </div>
          <div>
            <span class="font-medium text-gray-700 dark:text-gray-300">{{ p.enrollment_count ?? 0 }}</span>
            gesamt enrolled
          </div>
        </div>
      </button>
    </div>
  </div>
</template>
