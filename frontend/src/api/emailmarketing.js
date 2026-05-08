import api from '@/api'

const BASE = '/v1/emailmarketing'

// ============== Providers ==============

export function getProviders() {
  return api.get(`${BASE}/providers`)
}

export function getProvider(id) {
  return api.get(`${BASE}/providers/${id}`)
}

export function createProvider(data) {
  return api.post(`${BASE}/providers`, data)
}

export function updateProvider(id, data) {
  return api.put(`${BASE}/providers/${id}`, data)
}

export function deleteProvider(id) {
  return api.delete(`${BASE}/providers/${id}`)
}

export function verifyProvider(id) {
  return api.post(`${BASE}/providers/${id}/verify`)
}

/**
 * Aggregierte Versand-Statistiken vom Provider.
 * @param {number} id  Provider-ID
 * @param {object} params  { start_date, end_date?, aggregated_by? }
 */
export function getProviderStats(id, params = {}) {
  return api.get(`${BASE}/providers/${id}/stats`, { params })
}

// ============== Templates ==============

export function getTemplates(params = {}) {
  return api.get(`${BASE}/templates`, { params })
}

export function getTemplate(id) {
  return api.get(`${BASE}/templates/${id}`)
}

export function createTemplate(data) {
  return api.post(`${BASE}/templates`, data)
}

export function updateTemplate(id, data) {
  return api.put(`${BASE}/templates/${id}`, data)
}

export function deleteTemplate(id) {
  return api.delete(`${BASE}/templates/${id}`)
}

export function previewTemplate(data) {
  return api.post(`${BASE}/templates/preview`, data)
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

export function sendCampaign(id) {
  return api.post(`${BASE}/campaigns/${id}/send`)
}

export function scheduleCampaign(id, scheduledAt) {
  return api.post(`${BASE}/campaigns/${id}/schedule`, { scheduled_at: scheduledAt })
}

export function testCampaign(id, data) {
  return api.post(`${BASE}/campaigns/${id}/test`, data)
}

export function getCampaignStats(id) {
  return api.get(`${BASE}/campaigns/${id}/stats`)
}

export function getCampaignRecipients(id, params = {}) {
  return api.get(`${BASE}/campaigns/${id}/recipients`, { params })
}

// ============== Sequences ==============

export function getSequences(params = {}) {
  return api.get(`${BASE}/sequences`, { params })
}

export function getSequence(id) {
  return api.get(`${BASE}/sequences/${id}`)
}

export function createSequence(data) {
  return api.post(`${BASE}/sequences`, data)
}

export function updateSequence(id, data) {
  return api.put(`${BASE}/sequences/${id}`, data)
}

export function deleteSequence(id) {
  return api.delete(`${BASE}/sequences/${id}`)
}

export function activateSequence(id) {
  return api.post(`${BASE}/sequences/${id}/activate`)
}

export function pauseSequence(id) {
  return api.post(`${BASE}/sequences/${id}/pause`)
}

// ============== Sequence Steps ==============

export function addSequenceStep(sequenceId, data) {
  return api.post(`${BASE}/sequences/${sequenceId}/steps`, data)
}

export function updateSequenceStep(sequenceId, stepId, data) {
  return api.put(`${BASE}/sequences/${sequenceId}/steps/${stepId}`, data)
}

export function deleteSequenceStep(sequenceId, stepId) {
  return api.delete(`${BASE}/sequences/${sequenceId}/steps/${stepId}`)
}

// ============== Enrollments ==============

export function enrollContacts(sequenceId, contactIds) {
  return api.post(`${BASE}/sequences/${sequenceId}/enroll`, { contact_ids: contactIds })
}

export function getEnrollments(sequenceId, params = {}) {
  return api.get(`${BASE}/sequences/${sequenceId}/enrollments`, { params })
}

// ============== Config ==============

export function getEmailMarketingConfig() {
  return api.get(`${BASE}/config`)
}

export function updateEmailMarketingConfig(data) {
  return api.put(`${BASE}/config`, data)
}

export function getEmailMarketingStatus() {
  return api.get(`${BASE}/status`)
}

export function getEmailMarketingMetrics(days = 7) {
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
