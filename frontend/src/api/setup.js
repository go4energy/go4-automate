import api from '@/api'

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1'

export function createSetupConversation() {
  return api.post('/v1/setup/conversations')
}

export function listSetupConversations() {
  return api.get('/v1/setup/conversations')
}

export function getSetupConversation(id) {
  return api.get(`/v1/setup/conversations/${id}`)
}

export function deleteSetupConversation(id) {
  return api.delete(`/v1/setup/conversations/${id}`)
}

export async function sendSetupMessage(convId, content) {
  const tenantId = localStorage.getItem('tenant_id') || 'go4energy'
  const response = await fetch(`${API_BASE}/setup/conversations/${convId}/messages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Tenant-ID': tenantId
    },
    body: JSON.stringify({ content })
  })
  return response
}

export function getSetupStatus() {
  return api.get('/v1/setup/status')
}
