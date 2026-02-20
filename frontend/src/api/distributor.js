import api from '@/api'

export function getDistributorDashboard() {
  return api.get('/v1/distributor/dashboard')
}

export function getDistributorPerformance(params = {}) {
  return api.get('/v1/distributor/performance', { params })
}

export function getDistributorCampaigns() {
  return api.get('/v1/distributor/campaigns')
}

export function createCampaignConfig(data) {
  return api.post('/v1/distributor/campaigns/config', data)
}

export function updateCampaignConfig(configId, data) {
  return api.patch(`/v1/distributor/campaigns/${configId}/config`, data)
}

export function pauseCampaign(configId) {
  return api.post(`/v1/distributor/campaigns/${configId}/pause`)
}

export function resumeCampaign(configId) {
  return api.post(`/v1/distributor/campaigns/${configId}/resume`)
}

export function runOptimization() {
  return api.post('/v1/distributor/optimize')
}

export function getWeather() {
  return api.get('/v1/distributor/weather')
}

export function trackConversion(data) {
  return api.post('/v1/distributor/conversions', data)
}
