import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import {
  getChannels,
  getChannel,
  createChannel,
  updateChannel,
  deleteChannel,
  getEpisodes,
  generateEpisode,
  deleteEpisode,
  getUsers,
  createUser,
  deleteUser,
  getMetrics
} from '@/api/broadcaster'

export const useBroadcasterStore = defineStore('broadcaster', () => {
  const channels = ref([])
  const currentChannel = ref(null)
  const episodes = ref([])
  const users = ref([])
  const metrics = ref(null)
  const loading = ref(false)
  const generating = ref(false)
  const error = ref(null)

  const activeChannels = computed(() => channels.value.filter((c) => c.active))
  const totalEpisodes = computed(() =>
    channels.value.reduce((sum, c) => sum + (c.episode_count || 0), 0)
  )
  const totalListeners = computed(() =>
    channels.value.reduce((sum, c) => sum + (c.subscriber_count || 0), 0)
  )

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

  async function addChannel(channelData) {
    loading.value = true
    error.value = null
    try {
      const { data } = await createChannel(channelData)
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

  return {
    channels,
    currentChannel,
    episodes,
    users,
    metrics,
    loading,
    generating,
    error,
    activeChannels,
    totalEpisodes,
    totalListeners,
    fetchChannels,
    fetchChannel,
    addChannel,
    editChannel,
    removeChannel,
    fetchEpisodes,
    triggerGenerate,
    removeEpisode,
    fetchUsers,
    addUser,
    removeUser,
    fetchMetrics
  }
})
