import api from '@/api'

export function getContacts(params = {}) {
  return api.get('/v1/crm/', { params })
}

export function createContact(data) {
  return api.post('/v1/crm/', data)
}

export function updateContactStatus(contactId, status) {
  return api.patch(`/v1/crm/${contactId}/status`, { status })
}

export function pauseFollowup(contactId, paused) {
  return api.patch(`/v1/crm/${contactId}/pause-followup`, { paused })
}
