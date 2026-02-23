import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import {
  getGroups,
  createGroup,
  updateGroup,
  deleteGroup,
  getSources,
  getSource,
  createSource,
  updateSource,
  deleteSource,
  runCollector,
  getFindings,
  updateFinding,
  analyzeFinding,
  bulkDeleteFindings,
  getTopics,
  getTopic,
  createTopic,
  updateTopic,
  deleteTopic,
  generateFromTopic,
  reanalyzeTopic,
  bulkDeleteTopics,
  uploadImage,
  addGroupPrompt,
  removeGroupPrompt,
  runGroupPrompt
} from '@/api/collector'

const STORAGE_KEY = 'collector_active_group_id'

export const useCollectorStore = defineStore('collector', () => {
  const groups = ref([])
  const activeGroupId = ref(loadActiveGroupId())
  const sources = ref([])
  const findings = ref([])
  const topics = ref([])
  const currentSource = ref(null)
  const currentTopic = ref(null)
  const loading = ref(false)
  const error = ref(null)
  const runResult = ref(null)

  const activeSources = computed(() => sources.value.filter((s) => s.active))
  const suggestedTopics = computed(() => topics.value.filter((t) => t.status === 'suggested'))
  const newFindings = computed(() => findings.value.filter((f) => f.status === 'new'))
  const activeGroup = computed(() => groups.value.find((g) => g.id === activeGroupId.value) || null)

  function loadActiveGroupId() {
    const stored = localStorage.getItem(STORAGE_KEY)
    return stored ? Number(stored) : null
  }

  function selectGroup(groupId) {
    activeGroupId.value = groupId
    if (groupId) {
      localStorage.setItem(STORAGE_KEY, String(groupId))
    } else {
      localStorage.removeItem(STORAGE_KEY)
    }
  }

  function groupFilterParams(extra = {}) {
    const params = { ...extra }
    if (activeGroupId.value) {
      params.group_id = activeGroupId.value
    }
    return params
  }

  // --- Groups ---

  async function fetchGroups() {
    error.value = null
    try {
      const { data } = await getGroups()
      groups.value = data
      // If stored group no longer exists, reset to first group
      if (activeGroupId.value && !data.find((g) => g.id === activeGroupId.value)) {
        selectGroup(data.length > 0 ? data[0].id : null)
      }
      // If no group selected yet, select first
      if (!activeGroupId.value && data.length > 0) {
        selectGroup(data[0].id)
      }
    } catch (err) {
      error.value = err.message
    }
  }

  async function addGroup(groupData) {
    loading.value = true
    error.value = null
    try {
      const { data } = await createGroup(groupData)
      groups.value.push(data)
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function editGroup(id, groupData) {
    error.value = null
    try {
      const { data } = await updateGroup(id, groupData)
      const index = groups.value.findIndex((g) => g.id === id)
      if (index !== -1) groups.value[index] = data
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function removeGroup(id) {
    error.value = null
    try {
      await deleteGroup(id)
      groups.value = groups.value.filter((g) => g.id !== id)
      if (activeGroupId.value === id) {
        selectGroup(groups.value.length > 0 ? groups.value[0].id : null)
      }
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  // --- Sources ---

  async function fetchSources(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getSources(groupFilterParams(params))
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

  // --- Collector Run ---

  async function triggerCollector(sourceId = null) {
    loading.value = true
    error.value = null
    runResult.value = null
    try {
      const { data } = await runCollector({ source_id: sourceId })
      runResult.value = data
      await fetchFindings()
      await fetchTopics()
      await fetchGroups()
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
      const { data } = await getFindings(groupFilterParams(params))
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

  async function changeFindingGroup(id, groupId) {
    error.value = null
    try {
      const { data } = await updateFinding(id, { group_id: groupId })
      const index = findings.value.findIndex((f) => f.id === id)
      if (index !== -1) findings.value[index] = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function changeSourceGroup(id, groupId) {
    error.value = null
    try {
      const { data } = await updateSource(id, { group_id: groupId })
      const index = sources.value.findIndex((s) => s.id === id)
      if (index !== -1) sources.value[index] = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function changeTopicGroup(id, groupId) {
    error.value = null
    try {
      const { data } = await updateTopic(id, { group_id: groupId })
      const index = topics.value.findIndex((t) => t.id === id)
      if (index !== -1) topics.value[index] = data
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
      const { data } = await getTopics(groupFilterParams(params))
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

  async function fetchTopic(id) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getTopic(id)
      currentTopic.value = data
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function triggerReanalyze(id) {
    loading.value = true
    error.value = null
    try {
      const { data } = await reanalyzeTopic(id)
      currentTopic.value = { ...currentTopic.value, ...data }
      const index = topics.value.findIndex((t) => t.id === id)
      if (index !== -1) topics.value[index] = { ...topics.value[index], ...data }
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
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

  async function triggerAnalyzeFinding(findingId) {
    loading.value = true
    error.value = null
    try {
      const { data } = await analyzeFinding(findingId)
      await fetchTopics()
      await fetchGroups()
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function removeFindings(ids) {
    error.value = null
    try {
      const { data } = await bulkDeleteFindings(ids)
      findings.value = findings.value.filter((f) => !ids.includes(f.id))
      await fetchGroups()
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function removeTopics(ids) {
    error.value = null
    try {
      const { data } = await bulkDeleteTopics(ids)
      topics.value = topics.value.filter((t) => !ids.includes(t.id))
      await fetchGroups()
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function addPromptToGroup(groupId, purpose, sourceSlug = null) {
    loading.value = true
    error.value = null
    try {
      const payload = { purpose }
      if (sourceSlug) payload.source_slug = sourceSlug
      const { data } = await addGroupPrompt(groupId, payload)
      await fetchGroups()
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function removePromptFromGroup(groupId, slug) {
    loading.value = true
    error.value = null
    try {
      await removeGroupPrompt(groupId, slug)
      await fetchGroups()
      await fetchTopics()
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function runPromptForGroup(groupId, slug) {
    loading.value = true
    error.value = null
    try {
      const { data } = await runGroupPrompt(groupId, slug)
      await fetchTopics()
      await fetchGroups()
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
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
    groups,
    activeGroupId,
    activeGroup,
    sources,
    findings,
    topics,
    currentSource,
    currentTopic,
    loading,
    error,
    runResult,
    activeSources,
    suggestedTopics,
    newFindings,
    selectGroup,
    fetchGroups,
    addGroup,
    editGroup,
    removeGroup,
    fetchSources,
    fetchSource,
    addSource,
    editSource,
    removeSource,
    triggerCollector,
    fetchFindings,
    changeFindingStatus,
    changeFindingGroup,
    triggerAnalyzeFinding,
    removeFindings,
    changeSourceGroup,
    changeTopicGroup,
    fetchTopics,
    fetchTopic,
    addTopic,
    editTopic,
    removeTopic,
    removeTopics,
    triggerReanalyze,
    generateContent,
    addPromptToGroup,
    removePromptFromGroup,
    runPromptForGroup,
    upload
  }
})
