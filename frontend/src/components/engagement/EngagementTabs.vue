<script setup>
/**
 * Konsistente Tab-Bar für /engagement und /engagement/pipelines/:id/<tab>.
 * Pipelines-Tab führt zur Verwaltungstabelle, alle anderen Tabs gehen
 * zu der aktuell ausgewählten Pipeline.
 */
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { usePipelineContext } from '@/stores/pipelineContext'

const props = defineProps({
  activeTab: { type: String, required: true },
})

const router = useRouter()
const route = useRoute()
const pipelineCtx = usePipelineContext()

const tabs = computed(() => {
  const id = pipelineCtx.activePipelineId
  const detailPath = (sub) => (id ? `/engagement/pipelines/${id}/${sub}` : null)
  return [
    { key: 'pipelines', label: 'Pipelines', route: '/engagement', enabled: true },
    { key: 'uebersicht', label: 'Dashboard', route: detailPath('uebersicht'), enabled: !!id },
    { key: 'enrollments', label: 'Enrollments', route: detailPath('enrollments'), enabled: !!id },
    { key: 'actions', label: 'Aktionen', route: detailPath('actions'), enabled: !!id },
    { key: 'activities', label: 'Aktivitäten', route: detailPath('activities'), enabled: !!id },
    { key: 'ab-tests', label: 'A/B Tests', route: detailPath('ab-tests'), enabled: !!id },
    { key: 'setup', label: 'Setup', route: detailPath('setup'), enabled: !!id },
  ]
})

function go(tab) {
  if (!tab.enabled || !tab.route) return
  if (tab.route === route.path) return
  router.push(tab.route)
}
</script>

<template>
  <nav class="-mb-px flex gap-6 border-b border-gray-200 dark:border-gray-700">
    <button
      v-for="tab in tabs"
      :key="tab.key"
      type="button"
      class="border-b-2 pb-3 text-sm font-medium transition-colors"
      :class="[
        activeTab === tab.key
          ? 'border-go4-primary text-go4-primary'
          : tab.enabled
            ? 'border-transparent text-go4-muted hover:border-gray-300 hover:text-go4-secondary dark:text-gray-400 dark:hover:text-gray-300'
            : 'border-transparent text-gray-300 cursor-not-allowed dark:text-gray-600',
      ]"
      :disabled="!tab.enabled"
      :title="!tab.enabled ? 'Bitte zuerst eine Pipeline auswählen' : ''"
      @click="go(tab)"
    >
      {{ tab.label }}
    </button>
  </nav>
</template>
