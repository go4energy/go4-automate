import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import {
  getProfile,
  updateProfile as apiUpdateProfile,
  getSources,
  addSource as apiAddSource,
  updateSource as apiUpdateSource,
  deleteSource as apiDeleteSource,
  getItems,
  getRules,
  createRule as apiCreateRule,
  updateRule as apiUpdateRule,
  deleteRule as apiDeleteRule,
  getPendingActions,
  approveAction as apiApproveAction,
  rejectAction as apiRejectAction,
  addFeedback as apiAddFeedback,
  getDashboard,
} from '@/api/assistant'

export const useAssistantStore = defineStore('assistant', () => {
  // ── State ──
  const profile = ref(null)
  const sources = ref([])
  const items = ref([])
  const rules = ref([])
  const pendingActions = ref([])
  const dashboardStats = ref(null)

  const loading = ref(false)
  const error = ref(null)

  // ── Computed ──
  const activeRules = computed(() => rules.value.filter((r) => r.enabled))
  const connectedSources = computed(() => sources.value.length)

  // ── Profile ──
  async function fetchProfile() {
    loading.value = true
    error.value = null
    try {
      const { data } = await getProfile()
      profile.value = data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
    } finally {
      loading.value = false
    }
  }

  async function updateProfile(updates) {
    error.value = null
    try {
      const { data } = await apiUpdateProfile(updates)
      profile.value = data
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  // ── Sources ──
  async function fetchSources() {
    error.value = null
    try {
      const { data } = await getSources()
      sources.value = data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
    }
  }

  async function addSource(sourceData) {
    error.value = null
    try {
      const { data } = await apiAddSource(sourceData)
      sources.value.push(data)
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function updateSource(id, updates) {
    error.value = null
    try {
      const { data } = await apiUpdateSource(id, updates)
      const idx = sources.value.findIndex((s) => s.id === id)
      if (idx >= 0) sources.value[idx] = data
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function removeSource(id) {
    error.value = null
    try {
      await apiDeleteSource(id)
      sources.value = sources.value.filter((s) => s.id !== id)
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  // ── Items ──
  async function fetchItems(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getItems(params)
      items.value = data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
    } finally {
      loading.value = false
    }
  }

  async function sendFeedback(itemId, feedbackData) {
    error.value = null
    try {
      const { data } = await apiAddFeedback(itemId, feedbackData)
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  // ── Rules ──
  async function fetchRules() {
    error.value = null
    try {
      const { data } = await getRules()
      rules.value = data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
    }
  }

  async function addRule(ruleData) {
    error.value = null
    try {
      const { data } = await apiCreateRule(ruleData)
      rules.value.unshift(data)
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function editRule(id, updates) {
    error.value = null
    try {
      const { data } = await apiUpdateRule(id, updates)
      const idx = rules.value.findIndex((r) => r.id === id)
      if (idx >= 0) rules.value[idx] = data
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function removeRule(id) {
    error.value = null
    try {
      await apiDeleteRule(id)
      rules.value = rules.value.filter((r) => r.id !== id)
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  // ── Actions / Approvals ──
  async function fetchPendingActions() {
    error.value = null
    try {
      const { data } = await getPendingActions()
      pendingActions.value = data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
    }
  }

  async function approveAction(id) {
    error.value = null
    try {
      const { data } = await apiApproveAction(id)
      pendingActions.value = pendingActions.value.filter((a) => a.id !== id)
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function rejectAction(id) {
    error.value = null
    try {
      const { data } = await apiRejectAction(id)
      pendingActions.value = pendingActions.value.filter((a) => a.id !== id)
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  // ── Dashboard ──
  async function fetchDashboard() {
    error.value = null
    try {
      const { data } = await getDashboard()
      dashboardStats.value = data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
    }
  }

  return {
    // State
    profile,
    sources,
    items,
    rules,
    pendingActions,
    dashboardStats,
    loading,
    error,

    // Computed
    activeRules,
    connectedSources,

    // Methods
    fetchProfile,
    updateProfile,
    fetchSources,
    addSource,
    updateSource,
    removeSource,
    fetchItems,
    sendFeedback,
    fetchRules,
    addRule,
    editRule,
    removeRule,
    fetchPendingActions,
    approveAction,
    rejectAction,
    fetchDashboard,
  }
})
