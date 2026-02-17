import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import {
  getAdDashboard,
  getAdPerformance,
  getAdCampaigns,
  createCampaignConfig,
  updateCampaignConfig,
  pauseCampaign,
  resumeCampaign,
  runOptimization,
  getWeather
} from '@/api/ads'

export const useAdStore = defineStore('ads', () => {
  const dashboard = ref(null)
  const performance = ref([])
  const campaigns = ref([])
  const weather = ref(null)
  const optimizerLog = ref([])
  const loading = ref(false)
  const error = ref(null)

  const totalSpendToday = computed(() => {
    if (!dashboard.value) return '0.00'
    return Number(dashboard.value.today?.spend || 0).toFixed(2)
  })

  const totalLeadsToday = computed(() => {
    return dashboard.value?.today?.leads || 0
  })

  const activeCampaigns = computed(() => {
    return campaigns.value.filter((c) => c.status === 'active')
  })

  async function fetchDashboard() {
    loading.value = true
    error.value = null
    try {
      const { data } = await getAdDashboard()
      dashboard.value = data
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function fetchPerformance(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getAdPerformance(params)
      performance.value = data
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function fetchCampaigns() {
    error.value = null
    try {
      const { data } = await getAdCampaigns()
      campaigns.value = data
    } catch (err) {
      error.value = err.message
    }
  }

  async function addCampaignConfig(data) {
    error.value = null
    try {
      const { data: config } = await createCampaignConfig(data)
      campaigns.value.unshift(config)
      return config
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function editCampaignConfig(configId, data) {
    error.value = null
    try {
      const { data: config } = await updateCampaignConfig(configId, data)
      const index = campaigns.value.findIndex((c) => c.id === configId)
      if (index !== -1) campaigns.value[index] = config
      return config
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function pause(configId) {
    error.value = null
    try {
      await pauseCampaign(configId)
      const index = campaigns.value.findIndex((c) => c.id === configId)
      if (index !== -1) campaigns.value[index].status = 'paused'
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function resume(configId) {
    error.value = null
    try {
      await resumeCampaign(configId)
      const index = campaigns.value.findIndex((c) => c.id === configId)
      if (index !== -1) campaigns.value[index].status = 'active'
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function optimize() {
    loading.value = true
    error.value = null
    try {
      const { data } = await runOptimization()
      optimizerLog.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchWeather() {
    error.value = null
    try {
      const { data } = await getWeather()
      weather.value = data
    } catch (err) {
      error.value = err.message
    }
  }

  return {
    dashboard,
    performance,
    campaigns,
    weather,
    optimizerLog,
    loading,
    error,
    totalSpendToday,
    totalLeadsToday,
    activeCampaigns,
    fetchDashboard,
    fetchPerformance,
    fetchCampaigns,
    addCampaignConfig,
    editCampaignConfig,
    pause,
    resume,
    optimize,
    fetchWeather
  }
})
