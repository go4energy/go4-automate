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

export function listTopics() {
  return api.get('/v1/chat/topics')
}

export async function sendMessage(convId, content) {
  const tenantId = localStorage.getItem('tenant_id') || 'go4energy'
  const token = localStorage.getItem('token')
  const headers = {
    'Content-Type': 'application/json',
    'X-Tenant-ID': tenantId
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  const response = await fetch(`${API_BASE}/chat/conversations/${convId}/messages`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ content })
  })
  if (!response.ok) {
    const text = await response.text().catch(() => '')
    throw new Error(`Chat-Endpoint antwortet ${response.status}: ${text || response.statusText}`)
  }
  return response
}
