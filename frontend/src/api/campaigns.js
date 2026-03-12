import api from '@/api'

export function getCampaignsDashboard() {
  return api.get('/v1/campaigns/dashboard')
}

export function getCampaignsPerformance(params = {}) {
  return api.get('/v1/campaigns/performance', { params })
}

export function getCampaignsList() {
  return api.get('/v1/campaigns/list')
}

export function createCampaignConfig(data) {
  return api.post('/v1/campaigns/config', data)
}

export function updateCampaignConfig(configId, data) {
  return api.patch(`/v1/campaigns/${configId}/config`, data)
}

export function pauseCampaign(configId) {
  return api.post(`/v1/campaigns/${configId}/pause`)
}

export function resumeCampaign(configId) {
  return api.post(`/v1/campaigns/${configId}/resume`)
}

export function runOptimization() {
  return api.post('/v1/campaigns/optimize')
}

export function getWeather() {
  return api.get('/v1/campaigns/weather')
}

export function trackConversion(data) {
  return api.post('/v1/campaigns/conversions', data)
}
