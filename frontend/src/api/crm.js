import api from '@/api'

// ============== Legacy Contacts ==============

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

// ============== Pipelines ==============

export function getPipelines() {
  return api.get('/v1/crm/pipelines')
}

export function getPipeline(id) {
  return api.get(`/v1/crm/pipelines/${id}`)
}

export function createPipeline(data) {
  return api.post('/v1/crm/pipelines', data)
}

export function updatePipeline(id, data) {
  return api.put(`/v1/crm/pipelines/${id}`, data)
}

export function deletePipeline(id) {
  return api.delete(`/v1/crm/pipelines/${id}`)
}

// Stages
export function addStage(pipelineId, data) {
  return api.post(`/v1/crm/pipelines/${pipelineId}/stages`, data)
}

export function updateStage(stageId, data) {
  return api.put(`/v1/crm/stages/${stageId}`, data)
}

export function deleteStage(stageId) {
  return api.delete(`/v1/crm/stages/${stageId}`)
}

// ============== Deals ==============

export function getDeals(params = {}) {
  return api.get('/v1/crm/deals', { params })
}

export function getDeal(id) {
  return api.get(`/v1/crm/deals/${id}`)
}

export function getKanbanBoard(pipelineId) {
  return api.get(`/v1/crm/deals/kanban/${pipelineId}`)
}

export function createDeal(data) {
  return api.post('/v1/crm/deals', data)
}

export function updateDeal(id, data) {
  return api.put(`/v1/crm/deals/${id}`, data)
}

export function moveDeal(id, stageId) {
  return api.patch(`/v1/crm/deals/${id}/move`, { stage_id: stageId })
}

export function deleteDeal(id) {
  return api.delete(`/v1/crm/deals/${id}`)
}

// ============== Activities ==============

export function createActivity(data) {
  return api.post('/v1/crm/activities', data)
}

export function getContactActivities(contactId) {
  return api.get(`/v1/crm/activities/contact/${contactId}`)
}

export function getDealActivities(dealId) {
  return api.get(`/v1/crm/activities/deal/${dealId}`)
}

// ============== Tasks ==============

export function getTasks(params = {}) {
  return api.get('/v1/crm/tasks', { params })
}

export function getTask(id) {
  return api.get(`/v1/crm/tasks/${id}`)
}

export function createTask(data) {
  return api.post('/v1/crm/tasks', data)
}

export function updateTask(id, data) {
  return api.put(`/v1/crm/tasks/${id}`, data)
}

export function deleteTask(id) {
  return api.delete(`/v1/crm/tasks/${id}`)
}

// ============== Call Queue ==============

export function getCalls(params = {}) {
  return api.get('/v1/crm/calls', { params })
}

export function getCallStats() {
  return api.get('/v1/crm/calls/stats')
}

export function generateCallScript(actionId) {
  return api.post(`/v1/crm/calls/${actionId}/generate-script`)
}

export function logCall(actionId, data) {
  return api.post(`/v1/crm/calls/${actionId}/log`, data)
}
