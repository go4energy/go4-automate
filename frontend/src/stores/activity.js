import { ref } from 'vue'
import { defineStore } from 'pinia'
import api from '@/api'

export const useActivityStore = defineStore('activity', () => {
  const activities = ref([])
  const stats = ref([])
  const loading = ref(false)
  const error = ref(null)

  async function fetchActivities(module, limit = 50) {
    loading.value = true
    error.value = null
    try {
      const params = { limit }
      if (module) params.module = module
      const { data } = await api.get('/activities', { params })
      activities.value = data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
    } finally {
      loading.value = false
    }
  }

  async function fetchStats(days = 7) {
    try {
      const { data } = await api.get('/activities/stats', { params: { days } })
      stats.value = data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
    }
  }

  return { activities, stats, loading, error, fetchActivities, fetchStats }
})
