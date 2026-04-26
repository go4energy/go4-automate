import api from '@/api'

// Campaigns
export function listCampaigns(params = {}) {
  return api.get('/v1/leadgen/campaigns', { params })
}
export function getCampaign(id) {
  return api.get(`/v1/leadgen/campaigns/${id}`)
}
export function createCampaign(data) {
  return api.post('/v1/leadgen/campaigns', data)
}
export function updateCampaign(id, data) {
  return api.put(`/v1/leadgen/campaigns/${id}`, data)
}
export function deleteCampaign(id) {
  return api.delete(`/v1/leadgen/campaigns/${id}`)
}
export function getCampaignStats(id) {
  return api.get(`/v1/leadgen/campaigns/${id}/stats`)
}

// Runs
export function startRun(campaignId) {
  return api.post(`/v1/leadgen/campaigns/${campaignId}/runs`)
}
export function startEnrichRun(campaignId, { limit, sampling }) {
  return api.post(`/v1/leadgen/campaigns/${campaignId}/runs/enrich`, {
    limit,
    sampling
  })
}
export function listRunsForCampaign(campaignId) {
  return api.get(`/v1/leadgen/campaigns/${campaignId}/runs`)
}
export function getRun(id) {
  return api.get(`/v1/leadgen/runs/${id}`)
}
export function pauseRun(id) {
  return api.post(`/v1/leadgen/runs/${id}/pause`)
}
export function resumeRun(id, additionalBudget = null) {
  const body = additionalBudget ? { additional_budget: additionalBudget } : {}
  return api.post(`/v1/leadgen/runs/${id}/resume`, body)
}
export function advanceRunStage(id) {
  return api.post(`/v1/leadgen/runs/${id}/advance-stage`)
}

// Places
export function listPlacesForCampaign(campaignId, params = {}) {
  return api.get(`/v1/leadgen/campaigns/${campaignId}/places`, { params })
}
export function getPlace(id) {
  return api.get(`/v1/leadgen/places/${id}`)
}
export function rejectPlace(id, reason) {
  return api.post(`/v1/leadgen/places/${id}/reject`, { reason })
}

// LLM Intake
export function intakeCampaignParameters(text) {
  return api.post('/v1/leadgen/intake', { text })
}

// Handoff to Engagement
export function previewHandoff(campaignId, body) {
  return api.post(`/v1/leadgen/campaigns/${campaignId}/handoff/preview`, body)
}
export function executeHandoff(campaignId, body) {
  return api.post(`/v1/leadgen/campaigns/${campaignId}/handoff`, body)
}

// LinkedIn Sales Nav export
export function previewExport(campaignId, body) {
  return api.post(`/v1/leadgen/campaigns/${campaignId}/export/preview`, body)
}
export function downloadAccountsCsv(campaignId, params) {
  return api.get(`/v1/leadgen/campaigns/${campaignId}/export/sales-nav-accounts.csv`, {
    params,
    responseType: 'blob'
  })
}
export function downloadLeadsCsv(campaignId, params) {
  return api.get(`/v1/leadgen/campaigns/${campaignId}/export/sales-nav-leads.csv`, {
    params,
    responseType: 'blob'
  })
}
