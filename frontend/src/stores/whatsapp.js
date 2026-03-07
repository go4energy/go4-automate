import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import {
  getDashboard,
  getAccounts,
  getAccount,
  createAccount,
  updateAccount,
  deleteAccount,
  verifyAccount,
  getTemplates,
  getTemplate,
  syncTemplates,
  previewTemplate,
  getConversations,
  getConversation,
  createConversation,
  sendMessage,
  markConversationRead,
  getCampaigns,
  getCampaign,
  createCampaign,
  updateCampaign,
  deleteCampaign,
  generateCampaignRecipients,
  sendCampaign,
  scheduleCampaign,
  getCampaignStats,
  getCampaignRecipients,
  getWhatsAppStatus,
  getWhatsAppMetrics,
  getEngagementActions,
  generateActionContent,
  executeEngagementAction
} from '@/api/whatsapp'

export const useWhatsAppStore = defineStore('whatsapp', () => {
  // State
  const dashboard = ref(null)
  const accounts = ref([])
  const templates = ref([])
  const conversations = ref([])
  const campaigns = ref([])
  const currentAccount = ref(null)
  const currentTemplate = ref(null)
  const currentConversation = ref(null)
  const currentCampaign = ref(null)
  const campaignStats = ref(null)
  const campaignRecipients = ref([])
  const moduleStatus = ref(null)
  const moduleMetrics = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // Engagement Brain
  const engagementActions = ref([])
  const actionLoading = ref({})

  // Computed
  const activeAccounts = computed(() => accounts.value.filter((a) => a.status === 'active'))
  const openConversations = computed(() => conversations.value.filter((c) => c.status === 'open'))
  const unreadConversations = computed(() => conversations.value.filter((c) => c.unread_count > 0))
  const approvedTemplates = computed(() => templates.value.filter((t) => t.status === 'APPROVED'))
  const draftCampaigns = computed(() => campaigns.value.filter((c) => c.status === 'draft'))
  const sentCampaigns = computed(() => campaigns.value.filter((c) => c.status === 'sent'))

  // ============== Dashboard ==============

  async function fetchDashboard() {
    loading.value = true
    error.value = null
    try {
      const { data } = await getDashboard()
      dashboard.value = data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
    } finally {
      loading.value = false
    }
  }

  // ============== Accounts ==============

  async function fetchAccounts(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getAccounts(params)
      accounts.value = data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
    } finally {
      loading.value = false
    }
  }

  async function fetchAccount(id) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getAccount(id)
      currentAccount.value = data
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function addAccount(accountData) {
    loading.value = true
    error.value = null
    try {
      const { data } = await createAccount(accountData)
      accounts.value.unshift(data)
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function editAccount(id, accountData) {
    error.value = null
    try {
      const { data } = await updateAccount(id, accountData)
      const index = accounts.value.findIndex((a) => a.id === id)
      if (index !== -1) {
        accounts.value[index] = data
      }
      if (currentAccount.value?.id === id) {
        currentAccount.value = data
      }
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function removeAccount(id) {
    error.value = null
    try {
      await deleteAccount(id)
      accounts.value = accounts.value.filter((a) => a.id !== id)
      if (currentAccount.value?.id === id) {
        currentAccount.value = null
      }
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function checkAccount(id) {
    error.value = null
    try {
      const { data } = await verifyAccount(id)
      await fetchAccount(id)
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  // ============== Templates ==============

  async function fetchTemplates(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getTemplates(params)
      templates.value = data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
    } finally {
      loading.value = false
    }
  }

  async function fetchTemplate(id) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getTemplate(id)
      currentTemplate.value = data
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function syncAccountTemplates(accountId) {
    loading.value = true
    error.value = null
    try {
      const { data } = await syncTemplates(accountId)
      // Refresh templates
      await fetchTemplates({ account_id: accountId })
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function getTemplatePreview(templateId, variables = {}) {
    error.value = null
    try {
      const { data } = await previewTemplate(templateId, variables)
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  // ============== Conversations ==============

  async function fetchConversations(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getConversations(params)
      conversations.value = data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
    } finally {
      loading.value = false
    }
  }

  async function fetchConversation(id) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getConversation(id)
      currentConversation.value = data
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function startConversation(conversationData) {
    loading.value = true
    error.value = null
    try {
      const { data } = await createConversation(conversationData)
      conversations.value.unshift(data)
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function sendConversationMessage(conversationId, messageData) {
    error.value = null
    try {
      const { data } = await sendMessage(conversationId, messageData)
      // Add message to current conversation
      if (currentConversation.value?.id === conversationId) {
        currentConversation.value.messages.push(data)
        currentConversation.value.last_message_at = data.created_at
      }
      // Update in list
      const index = conversations.value.findIndex((c) => c.id === conversationId)
      if (index !== -1) {
        conversations.value[index].last_message_at = data.created_at
      }
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function markRead(conversationId) {
    error.value = null
    try {
      await markConversationRead(conversationId)
      // Update unread count
      const index = conversations.value.findIndex((c) => c.id === conversationId)
      if (index !== -1) {
        conversations.value[index].unread_count = 0
      }
      if (currentConversation.value?.id === conversationId) {
        currentConversation.value.unread_count = 0
      }
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  // ============== Campaigns ==============

  async function fetchCampaigns(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getCampaigns(params)
      campaigns.value = data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
    } finally {
      loading.value = false
    }
  }

  async function fetchCampaign(id) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getCampaign(id)
      currentCampaign.value = data
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function addCampaign(campaignData) {
    loading.value = true
    error.value = null
    try {
      const { data } = await createCampaign(campaignData)
      campaigns.value.unshift(data)
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function editCampaign(id, campaignData) {
    error.value = null
    try {
      const { data } = await updateCampaign(id, campaignData)
      const index = campaigns.value.findIndex((c) => c.id === id)
      if (index !== -1) {
        campaigns.value[index] = data
      }
      if (currentCampaign.value?.id === id) {
        currentCampaign.value = data
      }
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function removeCampaign(id) {
    error.value = null
    try {
      await deleteCampaign(id)
      campaigns.value = campaigns.value.filter((c) => c.id !== id)
      if (currentCampaign.value?.id === id) {
        currentCampaign.value = null
      }
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function generateRecipients(campaignId, defaultVariables = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await generateCampaignRecipients(campaignId, defaultVariables)
      // Refresh campaign to get updated recipient count
      await fetchCampaign(campaignId)
      return data.count
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function sendCampaignNow(id) {
    loading.value = true
    error.value = null
    try {
      const { data } = await sendCampaign(id)
      await fetchCampaign(id)
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function scheduleCampaignFor(id, scheduledAt) {
    error.value = null
    try {
      const { data } = await scheduleCampaign(id, scheduledAt)
      const index = campaigns.value.findIndex((c) => c.id === id)
      if (index !== -1) {
        campaigns.value[index] = data
      }
      if (currentCampaign.value?.id === id) {
        currentCampaign.value = data
      }
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function fetchCampaignStats(id) {
    error.value = null
    try {
      const { data } = await getCampaignStats(id)
      campaignStats.value = data
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function fetchCampaignRecipients(id, params = {}) {
    error.value = null
    try {
      const { data } = await getCampaignRecipients(id, params)
      campaignRecipients.value = data
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  // ============== Status & Metrics ==============

  async function fetchStatus() {
    try {
      const { data } = await getWhatsAppStatus()
      moduleStatus.value = data
      return data
    } catch (err) {
      // Silent fail
    }
  }

  async function fetchMetrics(days = 7) {
    try {
      const { data } = await getWhatsAppMetrics(days)
      moduleMetrics.value = data
      return data
    } catch (err) {
      // Silent fail
    }
  }

  // ============== Utils ==============

  function clearCurrent() {
    currentAccount.value = null
    currentTemplate.value = null
    currentConversation.value = null
    currentCampaign.value = null
    campaignStats.value = null
    campaignRecipients.value = []
  }

  function clearError() {
    error.value = null
  }

  // ============== Engagement Brain ==============

  async function fetchEngagementActions(status = null) {
    loading.value = true
    error.value = null
    try {
      const params = status ? { status } : {}
      const { data } = await getEngagementActions(params)
      engagementActions.value = data
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function generateContent(actionId) {
    actionLoading.value[actionId] = true
    error.value = null
    try {
      const { data } = await generateActionContent(actionId)
      // Update action in list with generated content
      const index = engagementActions.value.findIndex((a) => a.id === actionId)
      if (index !== -1) {
        engagementActions.value[index] = {
          ...engagementActions.value[index],
          generated_content: data.content
        }
      }
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      actionLoading.value[actionId] = false
    }
  }

  async function executeAction(actionId, contentOverride = null) {
    actionLoading.value[actionId] = true
    error.value = null
    try {
      const { data } = await executeEngagementAction(actionId, contentOverride)
      // Remove action from list after successful execution
      engagementActions.value = engagementActions.value.filter((a) => a.id !== actionId)
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      actionLoading.value[actionId] = false
    }
  }

  return {
    // State
    dashboard,
    accounts,
    templates,
    conversations,
    campaigns,
    currentAccount,
    currentTemplate,
    currentConversation,
    currentCampaign,
    campaignStats,
    campaignRecipients,
    moduleStatus,
    moduleMetrics,
    loading,
    error,
    // Computed
    activeAccounts,
    openConversations,
    unreadConversations,
    approvedTemplates,
    draftCampaigns,
    sentCampaigns,
    // Dashboard
    fetchDashboard,
    // Account Actions
    fetchAccounts,
    fetchAccount,
    addAccount,
    editAccount,
    removeAccount,
    checkAccount,
    // Template Actions
    fetchTemplates,
    fetchTemplate,
    syncAccountTemplates,
    getTemplatePreview,
    // Conversation Actions
    fetchConversations,
    fetchConversation,
    startConversation,
    sendConversationMessage,
    markRead,
    // Campaign Actions
    fetchCampaigns,
    fetchCampaign,
    addCampaign,
    editCampaign,
    removeCampaign,
    generateRecipients,
    sendCampaignNow,
    scheduleCampaignFor,
    fetchCampaignStats,
    fetchCampaignRecipients,
    // Status/Metrics
    fetchStatus,
    fetchMetrics,
    // Utils
    clearCurrent,
    clearError,
    // Engagement Brain
    engagementActions,
    actionLoading,
    fetchEngagementActions,
    generateContent,
    executeAction
  }
})
