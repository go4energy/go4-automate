import api from './index'

const BASE = '/v1/linkedin'

// ============== Stats ==============

export const getLinkedInStats = () => api.get(`${BASE}/stats`)

// ============== Accounts ==============

export const getAccounts = (params = {}) => api.get(`${BASE}/accounts`, { params })

export const getAccount = (id) => api.get(`${BASE}/accounts/${id}`)

export const createAccount = (data) => api.post(`${BASE}/accounts`, data)

export const updateAccount = (id, data) => api.patch(`${BASE}/accounts/${id}`, data)

export const deleteAccount = (id) => api.delete(`${BASE}/accounts/${id}`)

export const initiateLogin = (id, data = {}) => api.post(`${BASE}/accounts/${id}/login`, data)

export const verifySession = (id) => api.post(`${BASE}/accounts/${id}/verify`)

export const importSession = (id, data) => api.post(`${BASE}/accounts/${id}/import-session`, data)

export const setAccountPassword = (id, password) =>
  api.post(`${BASE}/accounts/${id}/set-password`, { password })

export const autoLogin = (id, password, waitTimeout = 120) =>
  api.post(`${BASE}/accounts/${id}/auto-login`, {
    password,
    wait_for_2fa_timeout: waitTimeout
  })

// ============== Jobs ==============

export const getJobs = (params = {}) => api.get(`${BASE}/jobs`, { params })

export const getJob = (id) => api.get(`${BASE}/jobs/${id}`)

export const createJob = (data) => api.post(`${BASE}/jobs`, data)

export const updateJob = (id, data) => api.patch(`${BASE}/jobs/${id}`, data)

export const deleteJob = (id) => api.delete(`${BASE}/jobs/${id}`)

export const startJob = (id) => api.post(`${BASE}/jobs/${id}/start`)

export const pauseJob = (id) => api.post(`${BASE}/jobs/${id}/pause`)

export const cancelJob = (id) => api.post(`${BASE}/jobs/${id}/cancel`)

export const addJobUrls = (id, urls) => api.post(`${BASE}/jobs/${id}/urls`, { urls })

// ============== Job Logs ==============

export const getJobLogs = (jobId, limit = 20) =>
  api.get(`${BASE}/jobs/${jobId}/logs`, { params: { limit } })

export const getJobLog = (jobId, logId) => api.get(`${BASE}/jobs/${jobId}/logs/${logId}`)

// ============== Contacts ==============

export const getJobContacts = (jobId) => api.get(`${BASE}/jobs/${jobId}/contacts`)

export const importJobContacts = (jobId, data) => api.post(`${BASE}/jobs/${jobId}/import`, data)

export const getAllContacts = (params = {}) => api.get(`${BASE}/contacts`, { params })

export const getContact = (id) => api.get(`${BASE}/contacts/${id}`)

export const toggleContactExclude = (id) => api.patch(`${BASE}/contacts/${id}/exclude`)

export const deleteContact = (id) => api.delete(`${BASE}/contacts/${id}`)

export const bulkDeleteContacts = (contactIds) =>
  api.post(`${BASE}/contacts/bulk-delete`, { contact_ids: contactIds })

export const deleteJobContacts = (jobId) => api.delete(`${BASE}/jobs/${jobId}/contacts`)

// ============== Templates ==============

export const getTemplates = (params = {}) => api.get(`${BASE}/templates`, { params })

export const getTemplate = (id) => api.get(`${BASE}/templates/${id}`)

export const createTemplate = (data) => api.post(`${BASE}/templates`, data)

export const updateTemplate = (id, data) => api.patch(`${BASE}/templates/${id}`, data)

export const deleteTemplate = (id) => api.delete(`${BASE}/templates/${id}`)

export const previewTemplate = (id, contactId) =>
  api.post(`${BASE}/templates/preview`, { template_id: id, contact_id: contactId })

// ============== Connections ==============

export const getConnections = (params = {}) => api.get(`${BASE}/connections`, { params })

export const getConnection = (id) => api.get(`${BASE}/connections/${id}`)

export const createConnection = (data) => api.post(`${BASE}/connections`, data)

export const createConnectionsBulk = (data) => api.post(`${BASE}/connections/bulk`, data)

export const withdrawConnection = (id) => api.post(`${BASE}/connections/${id}/withdraw`)

// ============== Messages ==============

export const getMessages = (params = {}) => api.get(`${BASE}/messages`, { params })

export const getInbox = (params = {}) => api.get(`${BASE}/inbox`, { params })

export const createMessage = (data) => api.post(`${BASE}/messages`, data)

// ============== Campaigns ==============

export const getCampaigns = (params = {}) => api.get(`${BASE}/campaigns`, { params })

export const getCampaign = (id) => api.get(`${BASE}/campaigns/${id}`)

export const createCampaign = (data) => api.post(`${BASE}/campaigns`, data)

export const updateCampaign = (id, data) => api.patch(`${BASE}/campaigns/${id}`, data)

export const deleteCampaign = (id) => api.delete(`${BASE}/campaigns/${id}`)

export const startCampaign = (id) => api.post(`${BASE}/campaigns/${id}/start`)

export const pauseCampaign = (id) => api.post(`${BASE}/campaigns/${id}/pause`)

// ============== Campaign Steps ==============

export const addCampaignStep = (campaignId, data) =>
  api.post(`${BASE}/campaigns/${campaignId}/steps`, data)

export const deleteCampaignStep = (campaignId, stepId) =>
  api.delete(`${BASE}/campaigns/${campaignId}/steps/${stepId}`)

// ============== Campaign Leads ==============

export const getCampaignLeads = (campaignId, params = {}) =>
  api.get(`${BASE}/campaigns/${campaignId}/leads`, { params })

export const addCampaignLead = (campaignId, data) =>
  api.post(`${BASE}/campaigns/${campaignId}/leads`, data)

export const addCampaignLeadsBulk = (campaignId, data) =>
  api.post(`${BASE}/campaigns/${campaignId}/leads/bulk`, data)

export const removeCampaignLead = (campaignId, leadId) =>
  api.delete(`${BASE}/campaigns/${campaignId}/leads/${leadId}`)

export const stopCampaignLead = (campaignId, leadId) =>
  api.post(`${BASE}/campaigns/${campaignId}/leads/${leadId}/stop`)

// ============== Immediate Actions ==============

export const sendConnectionRequest = (data) => api.post(`${BASE}/actions/send-connection`, data)

export const sendDirectMessage = (data) => api.post(`${BASE}/actions/send-message`, data)

// ============== Engagement Brain Actions ==============

export const getEngagementActions = (params = {}) =>
  api.get(`${BASE}/engagement/actions`, { params })

export const generateActionContent = (actionId) =>
  api.post(`${BASE}/engagement/actions/${actionId}/generate-content`)

export const executeEngagementAction = (actionId, contentOverride = null) =>
  api.post(`${BASE}/engagement/actions/${actionId}/execute`, {
    content_override: contentOverride
  })

// ============== Contact Bridge ==============

export const importToCentralContact = (contactId) =>
  api.post(`${BASE}/contacts/${contactId}/import-to-contacts`)

export const bulkImportToCentralContacts = (linkedinContactIds) =>
  api.post(`${BASE}/contacts/bulk-import-to-contacts`, {
    linkedin_contact_ids: linkedinContactIds
  })

export const linkToCentralContact = (linkedinContactId, contactId) =>
  api.post(`${BASE}/contacts/${linkedinContactId}/link-contact`, {
    contact_id: contactId
  })

export const importConversations = (linkedinContactId, contactId) =>
  api.post(`${BASE}/contacts/${linkedinContactId}/import-conversations`, {
    contact_id: contactId
  })
