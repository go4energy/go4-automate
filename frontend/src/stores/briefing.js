import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import {
  getChannels,
  getChannel,
  createChannel,
  updateChannel,
  deleteChannel,
  cloneChannel as apiCloneChannel,
  getEpisodes,
  generateEpisode,
  deleteEpisode,
  getUsers,
  createUser,
  deleteUser,
  getMetrics,
  getSources,
  getSource,
  createSource as apiCreateSource,
  updateSource as apiUpdateSource,
  deleteSource as apiDeleteSource,
  runSources as apiRunSources,
  runSource as apiRunSource,
  getFindings,
  updateFinding as apiUpdateFinding,
  bulkDeleteFindings as apiBulkDeleteFindings,
  getChannelSources,
  linkSource as apiLinkSource,
  unlinkSource as apiUnlinkSource,
  getSpeakers,
  uploadSpeaker,
  deleteSpeaker as apiDeleteSpeaker,
  disconnectOAuth as apiDisconnectOAuth
} from '@/api/briefing'

export const useBriefingStore = defineStore('briefing', () => {
  const channels = ref([])
  const currentChannel = ref(null)
  const episodes = ref([])
  const users = ref([])
  const metrics = ref(null)
  const sources = ref([])
  const findings = ref([])
  const channelSources = ref([])
  const speakers = ref([])
  const speakersLoading = ref(false)
  const loading = ref(false)
  const generating = ref(false)
  const sourcesLoading = ref(false)
  const findingsLoading = ref(false)
  const runningSource = ref(false)
  const error = ref(null)

  const activeChannels = computed(() => channels.value.filter((c) => c.active))
  const totalEpisodes = computed(() =>
    channels.value.reduce((sum, c) => sum + (c.episode_count || 0), 0)
  )
  const totalListeners = computed(() =>
    channels.value.reduce((sum, c) => sum + (c.subscriber_count || 0), 0)
  )
  const activeSources = computed(() => sources.value.filter((s) => s.active))
  const newFindings = computed(() => findings.value.filter((f) => f.status === 'new'))

  // User-scoped computed helpers
  const orgChannels = computed(() => channels.value.filter((c) => c.user_id === null))
  const myChannels = computed(() => channels.value.filter((c) => c.user_id !== null))
  const orgSources = computed(() => sources.value.filter((s) => s.user_id === null))
  const mySources = computed(() => sources.value.filter((s) => s.user_id !== null))

  // --- Channels ---

  async function fetchChannels() {
    loading.value = true
    error.value = null
    try {
      const { data } = await getChannels()
      channels.value = data
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function fetchChannel(id) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getChannel(id)
      currentChannel.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function addChannel(channelData, params) {
    loading.value = true
    error.value = null
    try {
      const { data } = await createChannel(channelData, params)
      channels.value.unshift(data)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function editChannel(id, channelData) {
    error.value = null
    try {
      const { data } = await updateChannel(id, channelData)
      const index = channels.value.findIndex((c) => c.id === id)
      if (index !== -1) channels.value[index] = data
      if (currentChannel.value?.id === id) currentChannel.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function removeChannel(id) {
    error.value = null
    try {
      await deleteChannel(id)
      channels.value = channels.value.filter((c) => c.id !== id)
      if (currentChannel.value?.id === id) currentChannel.value = null
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function cloneOrgChannel(channelId, overrides = {}) {
    error.value = null
    try {
      const { data } = await apiCloneChannel(channelId, overrides)
      channels.value.unshift(data)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // --- Episodes ---

  async function fetchEpisodes(channelId) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getEpisodes(channelId)
      episodes.value = data
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function triggerGenerate(channelId) {
    generating.value = true
    error.value = null
    try {
      const { data } = await generateEpisode(channelId)
      episodes.value.unshift(data)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      generating.value = false
    }
  }

  async function removeEpisode(id) {
    error.value = null
    try {
      await deleteEpisode(id)
      episodes.value = episodes.value.filter((e) => e.id !== id)
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // --- Users ---

  async function fetchUsers() {
    loading.value = true
    error.value = null
    try {
      const { data } = await getUsers()
      users.value = data
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function addUser(userData) {
    error.value = null
    try {
      const { data } = await createUser(userData)
      users.value.unshift(data)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function removeUser(id) {
    error.value = null
    try {
      await deleteUser(id)
      users.value = users.value.filter((u) => u.id !== id)
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // --- Metrics ---

  async function fetchMetrics(days = 7) {
    try {
      const { data } = await getMetrics(days)
      metrics.value = data
    } catch (err) {
      error.value = err.message
    }
  }

  // --- Sources ---

  async function fetchSources(params) {
    sourcesLoading.value = true
    error.value = null
    try {
      const { data } = await getSources(params)
      sources.value = data
    } catch (err) {
      error.value = err.message
    } finally {
      sourcesLoading.value = false
    }
  }

  async function fetchSource(id) {
    error.value = null
    try {
      const { data } = await getSource(id)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function addSource(sourceData, params) {
    error.value = null
    try {
      const { data } = await apiCreateSource(sourceData, params)
      sources.value.unshift(data)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function editSource(id, sourceData) {
    error.value = null
    try {
      const { data } = await apiUpdateSource(id, sourceData)
      const index = sources.value.findIndex((s) => s.id === id)
      if (index !== -1) sources.value[index] = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function removeSource(id) {
    error.value = null
    try {
      await apiDeleteSource(id)
      sources.value = sources.value.filter((s) => s.id !== id)
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function runAllSources() {
    runningSource.value = true
    error.value = null
    try {
      const { data } = await apiRunSources()
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      runningSource.value = false
    }
  }

  async function runSingleSource(id) {
    runningSource.value = true
    error.value = null
    try {
      const { data } = await apiRunSource(id)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      runningSource.value = false
    }
  }

  // --- Findings ---

  async function fetchFindings(params) {
    findingsLoading.value = true
    error.value = null
    try {
      const { data } = await getFindings(params)
      findings.value = data
    } catch (err) {
      error.value = err.message
    } finally {
      findingsLoading.value = false
    }
  }

  async function editFinding(id, findingData) {
    error.value = null
    try {
      const { data } = await apiUpdateFinding(id, findingData)
      const index = findings.value.findIndex((f) => f.id === id)
      if (index !== -1) findings.value[index] = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function bulkDeleteFindings(ids) {
    error.value = null
    try {
      const { data } = await apiBulkDeleteFindings(ids)
      findings.value = findings.value.filter((f) => !ids.includes(f.id))
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // --- Speakers ---

  async function fetchSpeakers() {
    speakersLoading.value = true
    error.value = null
    try {
      const { data } = await getSpeakers()
      speakers.value = data
    } catch (err) {
      error.value = err.message
    } finally {
      speakersLoading.value = false
    }
  }

  async function addSpeaker(formData) {
    error.value = null
    try {
      const { data } = await uploadSpeaker(formData)
      speakers.value.unshift(data)
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function removeSpeaker(id) {
    error.value = null
    try {
      await apiDeleteSpeaker(id)
      speakers.value = speakers.value.filter((s) => s.id !== id)
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // --- OAuth ---

  async function disconnectSourceOAuth(sourceId) {
    error.value = null
    try {
      const { data } = await apiDisconnectOAuth(sourceId)
      const index = sources.value.findIndex((s) => s.id === sourceId)
      if (index !== -1) sources.value[index] = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // --- Channel-Source Linking ---

  async function fetchChannelSources(channelId) {
    error.value = null
    try {
      const { data } = await getChannelSources(channelId)
      channelSources.value = data
      return data
    } catch (err) {
      error.value = err.message
    }
  }

  async function linkSourceToChannel(channelId, sourceId) {
    error.value = null
    try {
      await apiLinkSource(channelId, sourceId)
      await fetchChannelSources(channelId)
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function unlinkSourceFromChannel(channelId, sourceId) {
    error.value = null
    try {
      await apiUnlinkSource(channelId, sourceId)
      channelSources.value = channelSources.value.filter((s) => s.id !== sourceId)
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  return {
    channels,
    currentChannel,
    episodes,
    users,
    metrics,
    sources,
    findings,
    channelSources,
    speakers,
    speakersLoading,
    loading,
    generating,
    sourcesLoading,
    findingsLoading,
    runningSource,
    error,
    activeChannels,
    totalEpisodes,
    totalListeners,
    activeSources,
    newFindings,
    orgChannels,
    myChannels,
    orgSources,
    mySources,
    fetchChannels,
    fetchChannel,
    addChannel,
    editChannel,
    removeChannel,
    cloneOrgChannel,
    fetchEpisodes,
    triggerGenerate,
    removeEpisode,
    fetchUsers,
    addUser,
    removeUser,
    fetchMetrics,
    fetchSources,
    fetchSource,
    addSource,
    editSource,
    removeSource,
    runAllSources,
    runSingleSource,
    fetchFindings,
    editFinding,
    bulkDeleteFindings,
    disconnectSourceOAuth,
    fetchChannelSources,
    linkSourceToChannel,
    unlinkSourceFromChannel,
    fetchSpeakers,
    addSpeaker,
    removeSpeaker
  }
})
