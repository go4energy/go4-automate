import api from '@/api'

export function getAdDashboard() {
  return api.get('/v1/ads/dashboard')
}

export function getAdPerformance(params = {}) {
  return api.get('/v1/ads/performance', { params })
}

export function getAdCampaigns() {
  return api.get('/v1/ads/campaigns')
}

export function createCampaignConfig(data) {
  return api.post('/v1/ads/campaigns/config', data)
}

export function updateCampaignConfig(configId, data) {
  return api.patch(`/v1/ads/campaigns/${configId}/config`, data)
}

export function pauseCampaign(configId) {
  return api.post(`/v1/ads/campaigns/${configId}/pause`)
}

export function resumeCampaign(configId) {
  return api.post(`/v1/ads/campaigns/${configId}/resume`)
}

export function runOptimization() {
  return api.post('/v1/ads/optimize')
}

export function getWeather() {
  return api.get('/v1/ads/weather')
}

export function trackConversion(data) {
  return api.post('/v1/ads/conversions', data)
}
