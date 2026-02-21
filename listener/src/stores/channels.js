import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import api from '@/api'

export const useChannelsStore = defineStore('channels', () => {
  const channels = ref([])
  const subscriptions = ref([])
  const feed = ref([])
  const currentChannel = ref(null)
  const loading = ref(false)
  const error = ref(null)

  const subscribedIds = computed(() => subscriptions.value.map((s) => s.channel_id))

  async function fetchChannels() {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.get('/channels')
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
      const { data } = await api.get(`/channels/${id}`)
      currentChannel.value = data
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function fetchSubscriptions() {
    try {
      const { data } = await api.get('/subscriptions')
      subscriptions.value = data
    } catch {
      subscriptions.value = []
    }
  }

  async function subscribe(channelId) {
    try {
      await api.post('/subscriptions', { channel_id: channelId })
      await fetchSubscriptions()
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function unsubscribe(channelId) {
    try {
      await api.delete(`/subscriptions/${channelId}`)
      await fetchSubscriptions()
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function fetchFeed() {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.get('/feed')
      feed.value = data
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  return {
    channels,
    subscriptions,
    feed,
    currentChannel,
    loading,
    error,
    subscribedIds,
    fetchChannels,
    fetchChannel,
    fetchSubscriptions,
    subscribe,
    unsubscribe,
    fetchFeed
  }
})
