import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { useEngagementStore } from '@/stores/engagement'

export const usePipelineContext = defineStore('pipelineContext', () => {
  // Persisted in localStorage
  const activePipelineId = ref(
    parseInt(localStorage.getItem('activePipelineId')) || null
  )

  const engagementStore = useEngagementStore()

  // Active pipeline object (from engagement store)
  const activePipeline = computed(() => {
    if (!activePipelineId.value) return null
    return engagementStore.pipelines.find((p) => p.id === activePipelineId.value) || null
  })

  // Display label for header
  const label = computed(() => {
    if (!activePipeline.value) return 'Alle Pipelines'
    return activePipeline.value.name
  })

  // Is a pipeline selected?
  const isActive = computed(() => !!activePipelineId.value)

  function setActivePipeline(id) {
    activePipelineId.value = id
    if (id) {
      localStorage.setItem('activePipelineId', id)
    } else {
      localStorage.removeItem('activePipelineId')
    }
  }

  function clearPipeline() {
    setActivePipeline(null)
  }

  // Load pipelines if not already loaded
  async function ensurePipelines() {
    if (engagementStore.pipelines.length === 0) {
      await engagementStore.fetchPipelines()
    }
  }

  return {
    activePipelineId,
    activePipeline,
    label,
    isActive,
    setActivePipeline,
    clearPipeline,
    ensurePipelines
  }
})
