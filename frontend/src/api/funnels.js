import api from '@/api'

// ============== Funnels ==============

export function getFunnels(params = {}) {
  return api.get('/v1/funnels', { params })
}

export function getFunnel(id) {
  return api.get(`/v1/funnels/${id}`)
}

export function createFunnel(data) {
  return api.post('/v1/funnels', data)
}

export function updateFunnel(id, data) {
  return api.put(`/v1/funnels/${id}`, data)
}

export function deleteFunnel(id) {
  return api.delete(`/v1/funnels/${id}`)
}

// ============== Stages ==============

export function addStage(funnelId, data) {
  return api.post(`/v1/funnels/${funnelId}/stages`, data)
}

export function updateStage(stageId, data) {
  return api.put(`/v1/funnels/stages/${stageId}`, data)
}

export function deleteStage(stageId) {
  return api.delete(`/v1/funnels/stages/${stageId}`)
}

// ============== Companies ==============

export function getCompanies(funnelId, params = {}) {
  return api.get(`/v1/funnels/${funnelId}/companies`, { params })
}

export function getCompany(companyId) {
  return api.get(`/v1/funnels/companies/${companyId}`)
}

export function createCompany(funnelId, data) {
  return api.post(`/v1/funnels/${funnelId}/companies`, data)
}

export function updateCompany(companyId, data) {
  return api.put(`/v1/funnels/companies/${companyId}`, data)
}

export function deleteCompany(companyId) {
  return api.delete(`/v1/funnels/companies/${companyId}`)
}

// ============== Prospects ==============

export function getProspects(funnelId, params = {}) {
  return api.get(`/v1/funnels/${funnelId}/prospects`, { params })
}

export function getProspect(prospectId) {
  return api.get(`/v1/funnels/prospects/${prospectId}`)
}

export function getKanbanBoard(funnelId) {
  return api.get(`/v1/funnels/${funnelId}/kanban`)
}

export function createProspect(funnelId, data) {
  return api.post(`/v1/funnels/${funnelId}/prospects`, data)
}

export function updateProspect(prospectId, data) {
  return api.put(`/v1/funnels/prospects/${prospectId}`, data)
}

export function moveProspect(prospectId, stageId) {
  return api.patch(`/v1/funnels/prospects/${prospectId}/move`, { stage_id: stageId })
}

export function deleteProspect(prospectId) {
  return api.delete(`/v1/funnels/prospects/${prospectId}`)
}

// ============== Duplicate Check ==============

export function checkDuplicate(data) {
  return api.post('/v1/funnels/prospects/check-duplicate', data)
}

// ============== Bulk Import ==============

export function bulkImportProspects(funnelId, data) {
  return api.post(`/v1/funnels/${funnelId}/prospects/import`, data)
}

// ============== Activities ==============

export function createActivity(prospectId, data) {
  return api.post(`/v1/funnels/prospects/${prospectId}/activities`, data)
}

export function getProspectActivities(prospectId) {
  return api.get(`/v1/funnels/prospects/${prospectId}/activities`)
}

// ============== Handoffs ==============

export function initiateHandoff(prospectId, data) {
  return api.post(`/v1/funnels/prospects/${prospectId}/handoff`, data)
}

export function getHandoffs(params = {}) {
  return api.get('/v1/funnels/handoffs', { params })
}

export function retryHandoff(handoffId) {
  return api.post(`/v1/funnels/handoffs/${handoffId}/retry`)
}
