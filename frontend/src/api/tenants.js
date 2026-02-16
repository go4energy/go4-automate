import api from '@/api'

export function getTenants() {
  return api.get('/v1/tenants')
}

export function getTenant(tenantId) {
  return api.get(`/v1/tenants/${tenantId}`)
}
