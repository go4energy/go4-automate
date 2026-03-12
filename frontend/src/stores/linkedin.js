import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import {
  getLinkedInStats,
  getAccounts,
  getAccount,
  createAccount,
  updateAccount,
  deleteAccount,
  initiateLogin,
  verifySession,
  importSession,
  setAccountPassword,
  autoLogin,
  getJobs,
  getJob,
  createJob,
  updateJob,
  deleteJob,
  startJob,
  pauseJob,
  cancelJob,
  addJobUrls,
  getJobLogs,
  getJobContacts,
  importJobContacts,
  getAllContacts,
  getContact,
  toggleContactExclude,
  deleteContact,
  bulkDeleteContacts,
  deleteJobContacts,
  // Templates
  getTemplates,
  getTemplate,
  createTemplate,
  updateTemplate,
  deleteTemplate,
  previewTemplate,
  // Connections
  getConnections,
  createConnection,
  createConnectionsBulk,
  withdrawConnection,
  // Messages
  getMessages,
  getInbox,
  createMessage,
  // Campaigns
  getCampaigns,
  getCampaign,
  createCampaign,
  updateCampaign,
  deleteCampaign,
  startCampaign,
  pauseCampaign,
  addCampaignStep,
  deleteCampaignStep,
  getCampaignLeads,
  addCampaignLead,
  addCampaignLeadsBulk,
  removeCampaignLead,
  stopCampaignLead,
  // Actions
  sendConnectionRequest,
  sendDirectMessage,
  // Engagement Actions
  getEngagementActions,
  generateActionContent,
  executeEngagementAction
} from '@/api/linkedin'

export const useLinkedInStore = defineStore('linkedin', () => {
  // State
  const stats = ref(null)
  const accounts = ref([])
  const jobs = ref([])
  const contacts = ref([])
  const currentAccount = ref(null)
  const currentJob = ref(null)
  const currentContact = ref(null)
  const jobContacts = ref([])
  const jobLogs = ref([])
  const loading = ref(false)
  const error = ref(null)

  // Outreach State
  const templates = ref([])
  const currentTemplate = ref(null)
  const connections = ref([])
  const messages = ref([])
  const inbox = ref([])
  const campaigns = ref([])
  const currentCampaign = ref(null)
  const campaignLeads = ref([])
  // Engagement State
  const engagementActions = ref([])
  const actionLoading = ref({})

  // Computed
  const activeAccounts = computed(() => accounts.value.filter((a) => a.status === 'active'))

  const runningJobs = computed(() =>
    jobs.value.filter((j) => j.status === 'running' || j.status === 'queued')
  )

  const completedJobs = computed(() => jobs.value.filter((j) => j.status === 'completed'))

  // Outreach Computed
  const activeCampaigns = computed(() => campaigns.value.filter((c) => c.status === 'active'))

  const pendingConnections = computed(() => connections.value.filter((c) => c.status === 'pending'))

  const unreadMessages = computed(() => inbox.value.filter((m) => !m.read_at))

  // ============== Stats ==============

  async function fetchStats() {
    try {
      const { data } = await getLinkedInStats()
      stats.value = data
      return data
    } catch (err) {
      console.error('Failed to fetch LinkedIn stats:', err)
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
      error.value = err.message
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
      error.value = err.message
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
      error.value = err.message
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
      error.value = err.message
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
      error.value = err.message
      throw err
    }
  }

  async function loginAccount(id, headless = false) {
    error.value = null
    try {
      const { data } = await initiateLogin(id, { headless })
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function checkSession(id) {
    error.value = null
    try {
      const { data } = await verifySession(id)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function importAccountSession(id, liAtCookie) {
    error.value = null
    try {
      const sessionData = {
        cookies: [
          {
            name: 'li_at',
            value: liAtCookie,
            domain: '.linkedin.com',
            path: '/',
            secure: true,
            httpOnly: true
          }
        ]
      }
      const { data } = await importSession(id, sessionData)
      // Refresh accounts to update session status
      await fetchAccounts()
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function saveAccountPassword(id, password) {
    error.value = null
    try {
      const { data } = await setAccountPassword(id, password)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function startAutoLogin(id, password, waitTimeout = 120) {
    error.value = null
    try {
      const { data } = await autoLogin(id, password, waitTimeout)
      // Refresh accounts to update session status
      await fetchAccounts()
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // ============== Jobs ==============

  async function fetchJobs(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getJobs(params)
      jobs.value = data
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function fetchJob(id) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getJob(id)
      currentJob.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function addJob(jobData) {
    loading.value = true
    error.value = null
    try {
      const { data } = await createJob(jobData)
      jobs.value.unshift(data)
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function editJob(id, jobData) {
    error.value = null
    try {
      const { data } = await updateJob(id, jobData)
      const index = jobs.value.findIndex((j) => j.id === id)
      if (index !== -1) {
        jobs.value[index] = data
      }
      if (currentJob.value?.id === id) {
        currentJob.value = data
      }
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || err.message
      throw err
    }
  }

  async function removeJob(id) {
    error.value = null
    try {
      await deleteJob(id)
      jobs.value = jobs.value.filter((j) => j.id !== id)
      if (currentJob.value?.id === id) {
        currentJob.value = null
      }
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function runJob(id) {
    error.value = null
    try {
      const { data } = await startJob(id)
      // Merge response into existing job — startJob returns partial data (status, message, job_id)
      const index = jobs.value.findIndex((j) => j.id === id)
      if (index !== -1) {
        Object.assign(jobs.value[index], { status: data.status || 'running' })
      }
      if (currentJob.value?.id === id) {
        Object.assign(currentJob.value, { status: data.status || 'running' })
      }
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function stopJob(id) {
    error.value = null
    try {
      const { data } = await pauseJob(id)
      const index = jobs.value.findIndex((j) => j.id === id)
      if (index !== -1) {
        jobs.value[index] = data
      }
      if (currentJob.value?.id === id) {
        currentJob.value = data
      }
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function abortJob(id) {
    error.value = null
    try {
      const { data } = await cancelJob(id)
      const index = jobs.value.findIndex((j) => j.id === id)
      if (index !== -1) {
        jobs.value[index] = data
      }
      if (currentJob.value?.id === id) {
        currentJob.value = data
      }
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function addUrls(jobId, urls) {
    error.value = null
    try {
      const { data } = await addJobUrls(jobId, urls)
      // Refresh job to get updated URL count
      await fetchJob(jobId)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function fetchJobLogs(jobId, limit = 20) {
    error.value = null
    try {
      const { data } = await getJobLogs(jobId, limit)
      jobLogs.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // ============== Contacts ==============

  async function fetchJobContacts(jobId) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getJobContacts(jobId)
      jobContacts.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function importContacts(jobId, importData) {
    loading.value = true
    error.value = null
    try {
      const { data } = await importJobContacts(jobId, importData)
      // Refresh contacts
      await fetchJobContacts(jobId)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchAllContacts(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getAllContacts(params)
      contacts.value = data
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function fetchContact(id) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getContact(id)
      currentContact.value = data
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function toggleExclude(id) {
    try {
      const { data } = await toggleContactExclude(id)
      // Update in contacts list
      const idx = contacts.value.findIndex((c) => c.id === id)
      if (idx !== -1) contacts.value[idx].excluded = data.excluded
      // Update current contact if loaded
      if (currentContact.value?.id === id) currentContact.value.excluded = data.excluded
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function removeContact(id) {
    try {
      await deleteContact(id)
      contacts.value = contacts.value.filter((c) => c.id !== id)
      jobContacts.value = jobContacts.value.filter((c) => c.id !== id)
      if (currentContact.value?.id === id) currentContact.value = null
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function removeContactsBulk(contactIds) {
    try {
      const { data } = await bulkDeleteContacts(contactIds)
      contacts.value = contacts.value.filter((c) => !contactIds.includes(c.id))
      jobContacts.value = jobContacts.value.filter((c) => !contactIds.includes(c.id))
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function removeJobContacts(jobId) {
    try {
      await deleteJobContacts(jobId)
      jobContacts.value = []
      contacts.value = contacts.value.filter((c) => c.scraper_job_id !== jobId)
    } catch (err) {
      error.value = err.message
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
      error.value = err.message
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
      error.value = err.message
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
      error.value = err.message
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
      error.value = err.message
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
      error.value = err.message
      throw err
    }
  }

  async function renderTemplatePreview(templateId, contactId) {
    error.value = null
    try {
      const { data } = await previewTemplate(templateId, contactId)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // ============== Connections ==============

  async function fetchConnections(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getConnections(params)
      connections.value = data
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function addConnection(connectionData) {
    error.value = null
    try {
      const { data } = await createConnection(connectionData)
      connections.value.unshift(data)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function addConnectionsBulk(bulkData) {
    error.value = null
    try {
      const { data } = await createConnectionsBulk(bulkData)
      await fetchConnections()
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function cancelConnection(id) {
    error.value = null
    try {
      const { data } = await withdrawConnection(id)
      const index = connections.value.findIndex((c) => c.id === id)
      if (index !== -1) {
        connections.value[index] = data
      }
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // ============== Messages ==============

  async function fetchMessages(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getMessages(params)
      messages.value = data
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function fetchInbox(params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getInbox(params)
      inbox.value = data
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function sendMessage(messageData) {
    error.value = null
    try {
      const { data } = await createMessage(messageData)
      messages.value.unshift(data)
      return data
    } catch (err) {
      error.value = err.message
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
      error.value = err.message
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
      error.value = err.message
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
      error.value = err.message
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
      error.value = err.message
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
      error.value = err.message
      throw err
    }
  }

  async function runCampaign(id) {
    error.value = null
    try {
      const { data } = await startCampaign(id)
      const index = campaigns.value.findIndex((c) => c.id === id)
      if (index !== -1) {
        campaigns.value[index] = data
      }
      if (currentCampaign.value?.id === id) {
        currentCampaign.value = data
      }
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function stopCampaign(id) {
    error.value = null
    try {
      const { data } = await pauseCampaign(id)
      const index = campaigns.value.findIndex((c) => c.id === id)
      if (index !== -1) {
        campaigns.value[index] = data
      }
      if (currentCampaign.value?.id === id) {
        currentCampaign.value = data
      }
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // ============== Campaign Steps ==============

  async function createCampaignStep(campaignId, stepData) {
    error.value = null
    try {
      const { data } = await addCampaignStep(campaignId, stepData)
      if (currentCampaign.value?.id === campaignId) {
        currentCampaign.value.steps = data.steps
      }
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function removeCampaignStep(campaignId, stepId) {
    error.value = null
    try {
      await deleteCampaignStep(campaignId, stepId)
      if (currentCampaign.value?.id === campaignId) {
        currentCampaign.value.steps = currentCampaign.value.steps.filter((s) => s.id !== stepId)
      }
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // ============== Campaign Leads ==============

  async function fetchCampaignLeads(campaignId, params = {}) {
    loading.value = true
    error.value = null
    try {
      const { data } = await getCampaignLeads(campaignId, params)
      campaignLeads.value = data
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function addLeadToCampaign(campaignId, leadData) {
    error.value = null
    try {
      const { data } = await addCampaignLead(campaignId, leadData)
      campaignLeads.value.unshift(data)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function addLeadsToCampaignBulk(campaignId, contactIds) {
    error.value = null
    try {
      const { data } = await addCampaignLeadsBulk(campaignId, { contact_ids: contactIds })
      await fetchCampaignLeads(campaignId)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function removeLeadFromCampaign(campaignId, leadId) {
    error.value = null
    try {
      await removeCampaignLead(campaignId, leadId)
      campaignLeads.value = campaignLeads.value.filter((l) => l.id !== leadId)
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function pauseLeadInCampaign(campaignId, leadId) {
    error.value = null
    try {
      const { data } = await stopCampaignLead(campaignId, leadId)
      const index = campaignLeads.value.findIndex((l) => l.id === leadId)
      if (index !== -1) {
        campaignLeads.value[index] = data
      }
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // ============== Immediate Actions ==============

  async function sendConnectionNow(accountId, contactId, note = null, templateId = null) {
    error.value = null
    try {
      const { data } = await sendConnectionRequest({
        account_id: accountId,
        contact_id: contactId,
        note,
        template_id: templateId
      })
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function sendMessageNow(accountId, contactId, message, templateId = null) {
    error.value = null
    try {
      const { data } = await sendDirectMessage({
        account_id: accountId,
        contact_id: contactId,
        message,
        template_id: templateId
      })
      return data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // ============== Engagement Brain Actions ==============

  async function fetchEngagementActions(status = null) {
    loading.value = true
    error.value = null
    try {
      const params = status ? { status } : {}
      const { data } = await getEngagementActions(params)
      engagementActions.value = data
      return data
    } catch (err) {
      error.value = err.message
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
      // Update the action in the list with the generated content
      const index = engagementActions.value.findIndex((a) => a.id === actionId)
      if (index !== -1) {
        engagementActions.value[index].suggested_content = data.generated_content
      }
      return data
    } catch (err) {
      error.value = err.message
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
      // Remove the completed action from the list
      engagementActions.value = engagementActions.value.filter((a) => a.id !== actionId)
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      actionLoading.value[actionId] = false
    }
  }

  // ============== Utils ==============

  function clearCurrent() {
    currentAccount.value = null
    currentJob.value = null
    currentContact.value = null
    currentTemplate.value = null
    currentCampaign.value = null
    jobContacts.value = []
    jobLogs.value = []
    campaignLeads.value = []
  }

  return {
    // State
    stats,
    accounts,
    jobs,
    contacts,
    currentAccount,
    currentJob,
    currentContact,
    jobContacts,
    jobLogs,
    loading,
    error,
    // Outreach State
    templates,
    currentTemplate,
    connections,
    messages,
    inbox,
    campaigns,
    currentCampaign,
    campaignLeads,
    // Computed
    activeAccounts,
    runningJobs,
    completedJobs,
    activeCampaigns,
    pendingConnections,
    unreadMessages,
    // Stats
    fetchStats,
    // Account Actions
    fetchAccounts,
    fetchAccount,
    addAccount,
    editAccount,
    removeAccount,
    loginAccount,
    checkSession,
    importAccountSession,
    saveAccountPassword,
    startAutoLogin,
    // Job Actions
    fetchJobs,
    fetchJob,
    addJob,
    editJob,
    removeJob,
    runJob,
    stopJob,
    abortJob,
    addUrls,
    fetchJobLogs,
    // Contact Actions
    fetchJobContacts,
    importContacts,
    fetchAllContacts,
    fetchContact,
    toggleExclude,
    removeContact,
    removeContactsBulk,
    removeJobContacts,
    // Template Actions
    fetchTemplates,
    fetchTemplate,
    addTemplate,
    editTemplate,
    removeTemplate,
    renderTemplatePreview,
    // Connection Actions
    fetchConnections,
    addConnection,
    addConnectionsBulk,
    cancelConnection,
    // Message Actions
    fetchMessages,
    fetchInbox,
    sendMessage,
    // Campaign Actions
    fetchCampaigns,
    fetchCampaign,
    addCampaign,
    editCampaign,
    removeCampaign,
    runCampaign,
    stopCampaign,
    // Campaign Step Actions
    createCampaignStep,
    removeCampaignStep,
    // Campaign Lead Actions
    fetchCampaignLeads,
    addLeadToCampaign,
    addLeadsToCampaignBulk,
    removeLeadFromCampaign,
    pauseLeadInCampaign,
    // Immediate Actions
    sendConnectionNow,
    sendMessageNow,
    // Engagement Actions
    engagementActions,
    actionLoading,
    fetchEngagementActions,
    generateContent,
    executeAction,
    // Utils
    clearCurrent
  }
})
