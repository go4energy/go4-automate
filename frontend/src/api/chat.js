import api from '@/api'

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1'

export function createConversation(data) {
  return api.post('/v1/chat/conversations', data)
}

export function listConversations(status) {
  const params = {}
  if (status) params.status = status
  return api.get('/v1/chat/conversations', { params })
}

export function getConversation(id) {
  return api.get(`/v1/chat/conversations/${id}`)
}

export function deleteConversation(id) {
  return api.delete(`/v1/chat/conversations/${id}`)
}

export async function sendMessage(convId, content) {
  const tenantId = localStorage.getItem('tenant_id') || 'go4energy'
  const response = await fetch(`${API_BASE}/chat/conversations/${convId}/messages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Tenant-ID': tenantId
    },
    body: JSON.stringify({ content })
  })
  return response
}
