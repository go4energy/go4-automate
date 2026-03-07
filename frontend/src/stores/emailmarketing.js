import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import {
  getProviders,
  getProvider,
  createProvider,
  updateProvider,
  deleteProvider,
  verifyProvider,
  getTemplates,
  getTemplate,
  createTemplate,
  updateTemplate,
  deleteTemplate,
  getCampaigns,
  getCampaign,
  createCampaign,
  updateCampaign,
  deleteCampaign,
  sendCampaign,
  scheduleCampaign,
  testCampaign,
  getCampaignStats,
  getCampaignRecipients,
  getSequences,
  getSequence,
  createSequence,
  updateSequence,
  deleteSequence,
  activateSequence,
  pauseSequence,
  addSequenceStep,
  updateSequenceStep,
  deleteSequenceStep,
  enrollContacts,
  getEnrollments,
  getEmailMarketingStatus,
  getEmailMarketingMetrics,
  getEngagementActions,
  generateActionContent,
  executeEngagementAction
} from '@/api/emailmarketing'

export const useEmailMarketingStore = defineStore('emailmarketing', () => {
  // State
  const providers = ref([])
  const templates = ref([])
  const campaigns = ref([])
  const sequences = ref([])
  const currentProvider = ref(null)
  const currentTemplate = ref(null)
  const currentCampaign = ref(null)
  const currentSequence = ref(null)
  const campaignStats = ref(null)
  const campaignRecipients = ref([])
  const enrollments = ref([])
  const moduleStatus = ref(null)
  const moduleMetrics = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // Engagement Brain
  const engagementActions = ref([])
  const actionLoading = ref({})

  // Computed
  const activeProviders = computed(() => providers.value.filter((p) => p.status === 'active'))
  const draftCampaigns = computed(() => campaigns.value.filter((c) => c.status === 'draft'))
  const sentCampaigns = computed(() => campaigns.value.filter((c) => c.status === 'sent'))
  const activeSequences = computed(() => sequences.value.filter((s) => s.status === 'active'))
  const activeTemplates = computed(() => templates.value.filter((t) => t.is_active))

  // ============== Providers ==============

  async function fetchProviders() {
    loading.value = true
    error.value = null
    try {
      const { data } = await getProviders()
      providers.value = data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
    } finally {
      loading.value = false
    }
  }

  async function fetchProvider(id) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getProvider(id)
      currentProvider.value = data
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function addProvider(providerData) {
    loading.value = true
    error.value = null
    try {
      const { data } = await createProvider(providerData)
      providers.value.unshift(data)
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function editProvider(id, providerData) {
    error.value = null
    try {
      const { data } = await updateProvider(id, providerData)
      const index = providers.value.findIndex((p) => p.id === id)
      if (index !== -1) {
        providers.value[index] = data
      }
      if (currentProvider.value?.id === id) {
        currentProvider.value = data
      }
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function removeProvider(id) {
    error.value = null
    try {
      await deleteProvider(id)
      providers.value = providers.value.filter((p) => p.id !== id)
      if (currentProvider.value?.id === id) {
        currentProvider.value = null
      }
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function checkProvider(id) {
    error.value = null
    try {
      const { data } = await verifyProvider(id)
      // Refresh provider to get updated status
      await fetchProvider(id)
      return data.valid
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

  async function addTemplate(templateData) {
    loading.value = true
    error.value = null
    try {
      const { data } = await createTemplate(templateData)
      templates.value.unshift(data)
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function editTemplate(id, templateData) {
    error.value = null
    try {
      const { data } = await updateTemplate(id, templateData)
      const index = templates.value.findIndex((t) => t.id === id)
      if (index !== -1) {
        templates.value[index] = data
      }
      if (currentTemplate.value?.id === id) {
        currentTemplate.value = data
      }
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function removeTemplate(id) {
    error.value = null
    try {
      await deleteTemplate(id)
      templates.value = templates.value.filter((t) => t.id !== id)
      if (currentTemplate.value?.id === id) {
        currentTemplate.value = null
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

  async function sendCampaignNow(id) {
    loading.value = true
    error.value = null
    try {
      const { data } = await sendCampaign(id)
      // Refresh campaign to get updated status
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

  async function sendTestEmail(id, email, mergeData = {}) {
    error.value = null
    try {
      const { data } = await testCampaign(id, { to: email, merge_data: mergeData })
      return data.success
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

  // ============== Sequences ==============

  async function fetchSequences(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getSequences(params)
      sequences.value = data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
    } finally {
      loading.value = false
    }
  }

  async function fetchSequence(id) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getSequence(id)
      currentSequence.value = data
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function addSequence(sequenceData) {
    loading.value = true
    error.value = null
    try {
      const { data } = await createSequence(sequenceData)
      sequences.value.unshift(data)
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function editSequence(id, sequenceData) {
    error.value = null
    try {
      const { data } = await updateSequence(id, sequenceData)
      const index = sequences.value.findIndex((s) => s.id === id)
      if (index !== -1) {
        sequences.value[index] = data
      }
      if (currentSequence.value?.id === id) {
        currentSequence.value = data
      }
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function removeSequence(id) {
    error.value = null
    try {
      await deleteSequence(id)
      sequences.value = sequences.value.filter((s) => s.id !== id)
      if (currentSequence.value?.id === id) {
        currentSequence.value = null
      }
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function activateSequenceById(id) {
    error.value = null
    try {
      const { data } = await activateSequence(id)
      const index = sequences.value.findIndex((s) => s.id === id)
      if (index !== -1) {
        sequences.value[index] = data
      }
      if (currentSequence.value?.id === id) {
        currentSequence.value = data
      }
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function pauseSequenceById(id) {
    error.value = null
    try {
      const { data } = await pauseSequence(id)
      const index = sequences.value.findIndex((s) => s.id === id)
      if (index !== -1) {
        sequences.value[index] = data
      }
      if (currentSequence.value?.id === id) {
        currentSequence.value = data
      }
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  // ============== Sequence Steps ==============

  async function addStep(sequenceId, stepData) {
    error.value = null
    try {
      const { data } = await addSequenceStep(sequenceId, stepData)
      if (currentSequence.value?.id === sequenceId) {
        currentSequence.value.steps.push(data)
      }
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function editStep(sequenceId, stepId, stepData) {
    error.value = null
    try {
      const { data } = await updateSequenceStep(sequenceId, stepId, stepData)
      if (currentSequence.value?.id === sequenceId) {
        const index = currentSequence.value.steps.findIndex((s) => s.id === stepId)
        if (index !== -1) {
          currentSequence.value.steps[index] = data
        }
      }
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function removeStep(sequenceId, stepId) {
    error.value = null
    try {
      await deleteSequenceStep(sequenceId, stepId)
      if (currentSequence.value?.id === sequenceId) {
        currentSequence.value.steps = currentSequence.value.steps.filter((s) => s.id !== stepId)
      }
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  // ============== Enrollments ==============

  async function enrollContactsInSequence(sequenceId, contactIds) {
    error.value = null
    try {
      const { data } = await enrollContacts(sequenceId, contactIds)
      return data.enrolled
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function fetchEnrollments(sequenceId, params = {}) {
    error.value = null
    try {
      const { data } = await getEnrollments(sequenceId, params)
      enrollments.value = data
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  // ============== Status & Metrics ==============

  async function fetchStatus() {
    try {
      const { data } = await getEmailMarketingStatus()
      moduleStatus.value = data
      return data
    } catch (err) {
      // Silent fail
    }
  }

  async function fetchMetrics(days = 7) {
    try {
      const { data } = await getEmailMarketingMetrics(days)
      moduleMetrics.value = data
      return data
    } catch (err) {
      // Silent fail
    }
  }

  // ============== Utils ==============

  function clearCurrent() {
    currentProvider.value = null
    currentTemplate.value = null
    currentCampaign.value = null
    currentSequence.value = null
    campaignStats.value = null
    campaignRecipients.value = []
    enrollments.value = []
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
    providers,
    templates,
    campaigns,
    sequences,
    currentProvider,
    currentTemplate,
    currentCampaign,
    currentSequence,
    campaignStats,
    campaignRecipients,
    enrollments,
    moduleStatus,
    moduleMetrics,
    loading,
    error,
    // Computed
    activeProviders,
    draftCampaigns,
    sentCampaigns,
    activeSequences,
    activeTemplates,
    // Provider Actions
    fetchProviders,
    fetchProvider,
    addProvider,
    editProvider,
    removeProvider,
    checkProvider,
    // Template Actions
    fetchTemplates,
    fetchTemplate,
    addTemplate,
    editTemplate,
    removeTemplate,
    // Campaign Actions
    fetchCampaigns,
    fetchCampaign,
    addCampaign,
    editCampaign,
    removeCampaign,
    sendCampaignNow,
    scheduleCampaignFor,
    sendTestEmail,
    fetchCampaignStats,
    fetchCampaignRecipients,
    // Sequence Actions
    fetchSequences,
    fetchSequence,
    addSequence,
    editSequence,
    removeSequence,
    activateSequenceById,
    pauseSequenceById,
    // Step Actions
    addStep,
    editStep,
    removeStep,
    // Enrollment Actions
    enrollContactsInSequence,
    fetchEnrollments,
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
