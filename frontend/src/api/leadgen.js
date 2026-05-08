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
export function startEnrichRun(
  campaignId,
  {
    limit,
    sampling,
    stages,
    minMatchScore,
    enrichCompanies,
    apolloValidateExistingUrls,
    apolloRevealEmail,
    apolloRevealPhone
  }
) {
  // Backend accepts an optional `stages` subset to honour the unified
  // 'Run starten…' modal. Falls back to the legacy verify+llm default when
  // omitted so existing callers keep their behaviour.
  const body = { limit, sampling }
  if (stages && stages.length) body.stages = stages
  if (minMatchScore != null && minMatchScore !== '') body.min_match_score = Number(minMatchScore)
  if (enrichCompanies) body.enrich_companies = true
  if (apolloValidateExistingUrls) body.apollo_validate_existing_urls = true
  if (apolloRevealEmail) body.apollo_reveal_email = true
  if (apolloRevealPhone) body.apollo_reveal_phone = true
  return api.post(`/v1/leadgen/campaigns/${campaignId}/runs/enrich`, body)
}
export function previewEnrichRun(campaignId, { stages, minMatchScore, apolloValidateExistingUrls }) {
  // Body fields the backend ignores for preview (limit, sampling) still need
  // to satisfy the EnrichRunRequest schema, so we pass dummy defaults.
  const body = { limit: 1, sampling: 'top_rated' }
  if (stages && stages.length) body.stages = stages
  if (minMatchScore != null && minMatchScore !== '') body.min_match_score = Number(minMatchScore)
  if (apolloValidateExistingUrls) body.apollo_validate_existing_urls = true
  return api.post(`/v1/leadgen/campaigns/${campaignId}/runs/enrich/preview`, body)
}
export function listRunsForCampaign(campaignId) {
  return api.get(`/v1/leadgen/campaigns/${campaignId}/runs`)
}
export function getRun(id) {
  return api.get(`/v1/leadgen/runs/${id}`)
}
export function stopRun(id) {
  return api.post(`/v1/leadgen/runs/${id}/stop`)
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
export function getPlaceNeighbors(id, params = {}) {
  // params: { order_by, order_dir, status }
  return api.get(`/v1/leadgen/places/${id}/neighbors`, { params })
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
export function downloadApolloCsv(campaignId, params) {
  return api.get(`/v1/leadgen/campaigns/${campaignId}/export/apollo-contacts.csv`, {
    params,
    responseType: 'blob'
  })
}
