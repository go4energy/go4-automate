import { ref } from 'vue'
import { defineStore } from 'pinia'
import api from '@/api'

export const useFeedbackStore = defineStore('feedback', () => {
  const history = ref([])
  const loading = ref(false)
  const error = ref(null)

  async function submitFeedback(episodeId, rating, findingId) {
    error.value = null
    try {
      const payload = { episode_id: episodeId, rating }
      if (findingId) payload.finding_id = findingId
      await api.post('/feedback', payload)
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function fetchHistory() {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.get('/feedback/history')
      history.value = data
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  return { history, loading, error, submitFeedback, fetchHistory }
})
