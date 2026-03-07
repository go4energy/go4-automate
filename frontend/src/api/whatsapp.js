import api from '@/api'

const BASE = '/v1/whatsapp'

// ============== Dashboard ==============

export function getDashboard() {
  return api.get(`${BASE}/dashboard`)
}

// ============== Accounts ==============

export function getAccounts(params = {}) {
  return api.get(`${BASE}/accounts`, { params })
}

export function getAccount(id) {
  return api.get(`${BASE}/accounts/${id}`)
}

export function createAccount(data) {
  return api.post(`${BASE}/accounts`, data)
}

export function updateAccount(id, data) {
  return api.put(`${BASE}/accounts/${id}`, data)
}

export function deleteAccount(id) {
  return api.delete(`${BASE}/accounts/${id}`)
}

export function verifyAccount(id) {
  return api.post(`${BASE}/accounts/${id}/verify`)
}

// ============== Templates ==============

export function getTemplates(params = {}) {
  return api.get(`${BASE}/templates`, { params })
}

export function getTemplate(id) {
  return api.get(`${BASE}/templates/${id}`)
}

export function syncTemplates(accountId) {
  return api.post(`${BASE}/templates/sync`, null, { params: { account_id: accountId } })
}

export function previewTemplate(id, variables = {}) {
  return api.post(`${BASE}/templates/${id}/preview`, { variables })
}

// ============== Conversations ==============

export function getConversations(params = {}) {
  return api.get(`${BASE}/conversations`, { params })
}

export function getConversation(id) {
  return api.get(`${BASE}/conversations/${id}`)
}

export function createConversation(data) {
  return api.post(`${BASE}/conversations`, data)
}

export function sendMessage(conversationId, data) {
  return api.post(`${BASE}/conversations/${conversationId}/messages`, data)
}

export function markConversationRead(conversationId) {
  return api.post(`${BASE}/conversations/${conversationId}/read`)
}

// ============== Campaigns ==============

export function getCampaigns(params = {}) {
  return api.get(`${BASE}/campaigns`, { params })
}

export function getCampaign(id) {
  return api.get(`${BASE}/campaigns/${id}`)
}

export function createCampaign(data) {
  return api.post(`${BASE}/campaigns`, data)
}

export function updateCampaign(id, data) {
  return api.put(`${BASE}/campaigns/${id}`, data)
}

export function deleteCampaign(id) {
  return api.delete(`${BASE}/campaigns/${id}`)
}

export function generateCampaignRecipients(id, defaultVariables = {}) {
  return api.post(`${BASE}/campaigns/${id}/generate-recipients`, {
    default_variables: defaultVariables
  })
}

export function sendCampaign(id) {
  return api.post(`${BASE}/campaigns/${id}/send`)
}

export function scheduleCampaign(id, scheduledAt) {
  return api.post(`${BASE}/campaigns/${id}/schedule`, { scheduled_at: scheduledAt })
}

export function getCampaignStats(id) {
  return api.get(`${BASE}/campaigns/${id}/stats`)
}

export function getCampaignRecipients(id, params = {}) {
  return api.get(`${BASE}/campaigns/${id}/recipients`, { params })
}

// ============== Config ==============

export function getWhatsAppConfig() {
  return api.get(`${BASE}/config`)
}

export function updateWhatsAppConfig(data) {
  return api.put(`${BASE}/config`, data)
}

export function getWhatsAppStatus() {
  return api.get(`${BASE}/status`)
}

export function getWhatsAppMetrics(days = 7) {
  return api.get(`${BASE}/metrics`, { params: { days } })
}

// ============== Engagement Brain Actions ==============

export function getEngagementActions(params = {}) {
  return api.get(`${BASE}/engagement/actions`, { params })
}

export function generateActionContent(actionId) {
  return api.post(`${BASE}/engagement/actions/${actionId}/generate-content`)
}

export function executeEngagementAction(actionId, contentOverride = null) {
  return api.post(`${BASE}/engagement/actions/${actionId}/execute`, {
    content_override: contentOverride
  })
}
