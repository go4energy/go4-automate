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
  getOAuthUrl,
  runIntake as apiRunIntake,
  runClassify as apiRunClassify,
  runRules as apiRunRules,
  runBriefing as apiRunBriefing,
  getRuleSuggestions as apiGetRuleSuggestions,
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

  // ── OAuth ──
  async function connectAccount(provider, sharedMailbox = null) {
    error.value = null
    try {
      const params = { provider }
      if (sharedMailbox) params.shared_mailbox = sharedMailbox
      const { data } = await getOAuthUrl(params)
      const popup = window.open(data.auth_url, 'assistant_oauth', 'width=600,height=700')

      return new Promise((resolve) => {
        const handler = (event) => {
          if (event.data?.type === 'oauth_success') {
            window.removeEventListener('message', handler)
            fetchSources()
            resolve(true)
          } else if (event.data?.type === 'oauth_error') {
            window.removeEventListener('message', handler)
            error.value = event.data.error || 'OAuth fehlgeschlagen'
            resolve(false)
          }
        }
        window.addEventListener('message', handler)

        const checkClosed = setInterval(() => {
          if (popup?.closed) {
            clearInterval(checkClosed)
            window.removeEventListener('message', handler)
            fetchSources()
            resolve(false)
          }
        }, 1000)
      })
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  // ── Test Triggers ──
  const testResults = ref([])
  const briefingText = ref('')
  const ruleSuggestions = ref([])

  async function triggerIntake() {
    error.value = null
    try {
      const { data } = await apiRunIntake()
      testResults.value.unshift({ action: 'Intake', time: new Date(), ...data })
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function triggerClassify() {
    error.value = null
    try {
      const { data } = await apiRunClassify()
      testResults.value.unshift({ action: 'Classify', time: new Date(), ...data })
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function triggerRules() {
    error.value = null
    try {
      const { data } = await apiRunRules()
      testResults.value.unshift({ action: 'Rules', time: new Date(), ...data })
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function triggerBriefing() {
    error.value = null
    try {
      const { data } = await apiRunBriefing()
      briefingText.value = data.briefing_text || ''
      testResults.value.unshift({
        action: 'Briefing',
        time: new Date(),
        items_processed: data.items_processed,
        actions_created: data.actions_created,
      })
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function triggerFullPipeline() {
    await triggerIntake()
    await triggerClassify()
    await triggerRules()
    await triggerBriefing()
    await fetchItems()
  }

  async function fetchRuleSuggestions() {
    error.value = null
    try {
      const { data } = await apiGetRuleSuggestions()
      ruleSuggestions.value = data
    } catch (err) {
      error.value = err.message
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
    testResults,
    briefingText,
    ruleSuggestions,
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
    connectAccount,
    approveAction,
    rejectAction,
    triggerIntake,
    triggerClassify,
    triggerRules,
    triggerBriefing,
    triggerFullPipeline,
    fetchRuleSuggestions,
    fetchDashboard,
  }
})
