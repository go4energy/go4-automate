import api from '@/api'

// Dashboard
export function getDashboardStats() {
  return api.get('/v1/customer-journey/dashboard/stats')
}

export function getDashboardFeed(params = {}) {
  return api.get('/v1/customer-journey/dashboard/feed', { params })
}

export function getFeedPage(params = {}) {
  return api.get('/v1/customer-journey/dashboard/feed', { params })
}

export function getFeedSources() {
  return api.get('/v1/customer-journey/dashboard/sources')
}

export function getDashboardFeedByLead(params = {}) {
  return api.get('/v1/customer-journey/dashboard/feed-by-lead', { params })
}

// Leads
export function getLeads(params = {}) {
  return api.get('/v1/customer-journey/leads', { params })
}

export function getLeadTimeline(contactId, params = {}) {
  return api.get(`/v1/customer-journey/leads/${contactId}/timeline`, { params })
}

// Ref-Codes
export function getRefCodes(params = {}) {
  return api.get('/v1/customer-journey/refs', { params })
}

export function createRefCode(data) {
  return api.post('/v1/customer-journey/refs', data)
}

export function bulkCreateRefCodes(data) {
  return api.post('/v1/customer-journey/refs/bulk', data)
}

export function updateRefCode(id, data) {
  return api.put(`/v1/customer-journey/refs/${id}`, data)
}

export function deleteRefCode(id) {
  return api.delete(`/v1/customer-journey/refs/${id}`)
}

// CSV Import
export function getImportFields() {
  return api.get('/v1/customer-journey/import/fields')
}

export function importPreview(data) {
  return api.post('/v1/customer-journey/import/preview', data)
}

export function importExecute(data) {
  return api.post('/v1/customer-journey/import/execute', data, { responseType: 'blob' })
}

// Campaigns
export function getCampaigns(params = {}) {
  return api.get('/v1/customer-journey/campaigns', { params })
}

export function createCampaign(data) {
  return api.post('/v1/customer-journey/campaigns', data)
}

export function updateCampaign(id, data) {
  return api.put(`/v1/customer-journey/campaigns/${id}`, data)
}

export function deleteCampaign(id) {
  return api.delete(`/v1/customer-journey/campaigns/${id}`)
}
