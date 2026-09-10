<script setup>
import { computed, onMounted } from 'vue'
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
const activeTab = computed(() => route.meta?.tab || 'briefings')

onMounted(() => store.fetchBriefings({ limit: 50 }))
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

    <div
      v-if="store.briefings.length === 0"
      class="rounded-lg border-2 border-dashed border-gray-200 p-12 text-center text-sm text-go4-muted dark:border-gray-700 dark:text-gray-400"
    >
      Noch keine Briefings.
    </div>
    <ul v-else class="space-y-3">
      <li
        v-for="b in store.briefings"
        :key="b.id"
        class="cursor-pointer rounded-lg border border-gray-200 bg-white p-5 hover:shadow-md dark:border-gray-700 dark:bg-gray-800"
        @click="router.push(`/intel/briefings/${b.id}`)"
      >
        <div class="flex items-start justify-between gap-4">
          <div class="min-w-0 flex-1">
            <p class="text-sm font-medium text-go4-secondary dark:text-gray-100">
              {{ new Date(b.period_end).toLocaleDateString('de-DE') }} ·
              {{ (b.payload?.sections || []).length }} Sektionen
            </p>
            <p class="mt-1 text-sm text-go4-muted dark:text-gray-300">{{ b.tts_summary }}</p>
          </div>
          <span class="whitespace-nowrap text-xs text-gray-400">
            {{ new Date(b.created_at).toLocaleString('de-DE') }}
          </span>
        </div>
      </li>
    </ul>
  </div>
</template>
