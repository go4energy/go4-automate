import api from '@/api'

export function getLeads(params = {}) {
  return api.get('/v1/leads', { params })
}

export function createLead(data) {
  return api.post('/v1/leads', data)
}

export function updateLeadStatus(leadId, status) {
  return api.patch(`/v1/leads/${leadId}/status`, { status })
}

export function pauseFollowup(leadId, paused) {
  return api.patch(`/v1/leads/${leadId}/pause-followup`, { paused })
}
