import api from '@/api'

export function getEnabledModules() {
  return api.get('/api/v1/licensing/enabled')
}

export function getLicenses() {
  return api.get('/api/v1/licensing/licenses')
}

export function grantLicense(payload) {
  return api.post('/api/v1/licensing/licenses', payload)
}

export function revokeLicense(moduleKey) {
  return api.delete(`/api/v1/licensing/licenses/${moduleKey}`)
}
