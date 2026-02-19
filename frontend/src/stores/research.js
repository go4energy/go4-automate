import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import {
  getSources,
  getSource,
  createSource,
  updateSource,
  deleteSource,
  runResearch,
  getFindings,
  updateFinding,
  getTopics,
  createTopic,
  updateTopic,
  deleteTopic,
  generateFromTopic,
  uploadImage
} from '@/api/research'

export const useResearchStore = defineStore('research', () => {
  const sources = ref([])
  const findings = ref([])
  const topics = ref([])
  const currentSource = ref(null)
  const loading = ref(false)
  const error = ref(null)
  const runResult = ref(null)

  const activeSources = computed(() => sources.value.filter((s) => s.active))
  const suggestedTopics = computed(() => topics.value.filter((t) => t.status === 'suggested'))
  const newFindings = computed(() => findings.value.filter((f) => f.status === 'new'))

  // --- Sources ---

  async function fetchSources(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getSources(params)
      sources.value = data
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function fetchSource(id) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getSource(id)
      currentSource.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function addSource(sourceData) {
    loading.value = true
    error.value = null
    try {
      const { data } = await createSource(sourceData)
      sources.value.unshift(data)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function editSource(id, sourceData) {
    error.value = null
    try {
      const { data } = await updateSource(id, sourceData)
      const index = sources.value.findIndex((s) => s.id === id)
      if (index !== -1) sources.value[index] = data
      if (currentSource.value?.id === id) currentSource.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function removeSource(id) {
    error.value = null
    try {
      await deleteSource(id)
      sources.value = sources.value.filter((s) => s.id !== id)
      if (currentSource.value?.id === id) currentSource.value = null
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // --- Research Run ---

  async function triggerResearch(sourceId = null) {
    loading.value = true
    error.value = null
    runResult.value = null
    try {
      const { data } = await runResearch({ source_id: sourceId })
      runResult.value = data
      await fetchFindings()
      await fetchTopics()
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  // --- Findings ---

  async function fetchFindings(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getFindings(params)
      findings.value = data
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function changeFindingStatus(id, status) {
    error.value = null
    try {
      const { data } = await updateFinding(id, { status })
      const index = findings.value.findIndex((f) => f.id === id)
      if (index !== -1) findings.value[index] = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // --- Topics ---

  async function fetchTopics(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getTopics(params)
      topics.value = data
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function addTopic(topicData) {
    loading.value = true
    error.value = null
    try {
      const { data } = await createTopic(topicData)
      topics.value.unshift(data)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function editTopic(id, topicData) {
    error.value = null
    try {
      const { data } = await updateTopic(id, topicData)
      const index = topics.value.findIndex((t) => t.id === id)
      if (index !== -1) topics.value[index] = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function removeTopic(id) {
    error.value = null
    try {
      await deleteTopic(id)
      topics.value = topics.value.filter((t) => t.id !== id)
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function generateContent(topicId, platform, contentType) {
    loading.value = true
    error.value = null
    try {
      const { data } = await generateFromTopic(topicId, {
        platform,
        content_type: contentType
      })
      await fetchTopics()
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function upload(file) {
    error.value = null
    try {
      const { data } = await uploadImage(file)
      return data.url
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  return {
    sources,
    findings,
    topics,
    currentSource,
    loading,
    error,
    runResult,
    activeSources,
    suggestedTopics,
    newFindings,
    fetchSources,
    fetchSource,
    addSource,
    editSource,
    removeSource,
    triggerResearch,
    fetchFindings,
    changeFindingStatus,
    fetchTopics,
    addTopic,
    editTopic,
    removeTopic,
    generateContent,
    upload
  }
})
