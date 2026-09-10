import { defineStore } from 'pinia'
import { ref } from 'vue'
import { intelApi } from '@/api/intel'

export const useIntelStore = defineStore('intel', () => {
  const targets = ref([])
  const sources = ref({}) // keyed by targetId
  const briefings = ref([])
  const events = ref([])
  const loading = ref(false)
  const error = ref(null)
  const embedStatus = ref(null)

  async function fetchTargets() {
    loading.value = true
    error.value = null
    try {
      targets.value = await intelApi.listTargets()
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
    } finally {
      loading.value = false
    }
  }

  async function createTarget(payload) {
    const created = await intelApi.createTarget(payload)
    targets.value.push(created)
    return created
  }

  async function updateTarget(id, payload) {
    const updated = await intelApi.updateTarget(id, payload)
    const idx = targets.value.findIndex((t) => t.id === id)
    if (idx >= 0) targets.value[idx] = updated
    return updated
  }

  async function deleteTarget(id) {
    await intelApi.deleteTarget(id)
    targets.value = targets.value.filter((t) => t.id !== id)
  }

  async function fetchSources(targetId) {
    sources.value[targetId] = await intelApi.listSources(targetId)
    return sources.value[targetId]
  }

  async function createSource(targetId, payload) {
    const created = await intelApi.createSource(targetId, payload)
    if (!sources.value[targetId]) sources.value[targetId] = []
    sources.value[targetId].push(created)
    return created
  }

  async function updateSource(sourceId, payload) {
    return intelApi.updateSource(sourceId, payload)
  }

  async function deleteSource(sourceId) {
    return intelApi.deleteSource(sourceId)
  }

  async function fetchBriefings(params = {}) {
    briefings.value = await intelApi.listBriefings(params)
  }

  async function fetchEvents(params = {}) {
    events.value = await intelApi.listEvents(params)
  }

  async function probeEmbedding() {
    embedStatus.value = await intelApi.embedHealth()
    return embedStatus.value
  }

  async function runNow() {
    return intelApi.runNow()
  }

  return {
    targets,
    sources,
    briefings,
    events,
    loading,
    error,
    embedStatus,
    fetchTargets,
    createTarget,
    updateTarget,
    deleteTarget,
    fetchSources,
    createSource,
    updateSource,
    deleteSource,
    fetchBriefings,
    fetchEvents,
    probeEmbedding,
    runNow
  }
})
