import api from '@/api'

// ============== Dashboard ==============

export function getDashboard() {
  return api.get('/v1/engagement/dashboard')
}

// ============== Pipelines ==============

export function getPipelines(params = {}) {
  return api.get('/v1/engagement/pipelines', { params })
}

export function getPipeline(id) {
  return api.get(`/v1/engagement/pipelines/${id}`)
}

export function createPipeline(data) {
  return api.post('/v1/engagement/pipelines', data)
}

export function updatePipeline(id, data) {
  return api.put(`/v1/engagement/pipelines/${id}`, data)
}

export function deletePipeline(id) {
  return api.delete(`/v1/engagement/pipelines/${id}`)
}

export function getPipelineStats(id) {
  return api.get(`/v1/engagement/pipelines/${id}/stats`)
}

export function getPipelineFunnel(id) {
  return api.get(`/v1/engagement/pipelines/${id}/funnel`)
}

// ============== Enrollments ==============

export function getEnrollments(params = {}) {
  return api.get('/v1/engagement/enrollments', { params })
}

export function getEnrollment(id) {
  return api.get(`/v1/engagement/enrollments/${id}`)
}

export function enrollContact(data) {
  return api.post('/v1/engagement/enrollments', data)
}

export function bulkEnrollContacts(data) {
  return api.post('/v1/engagement/enrollments/bulk', data)
}

export function updateEnrollment(id, data) {
  return api.put(`/v1/engagement/enrollments/${id}`, data)
}

export function unenrollContact(id) {
  return api.post(`/v1/engagement/enrollments/${id}/unenroll`)
}

// ============== Pending Actions ==============

export function getActions(params = {}) {
  return api.get('/v1/engagement/actions', { params })
}

export function getApprovalQueue(module = null) {
  const params = module ? { module } : {}
  return api.get('/v1/engagement/actions/approval-queue', { params })
}

export function getAction(id) {
  return api.get(`/v1/engagement/actions/${id}`)
}

export function createAction(data) {
  return api.post('/v1/engagement/actions', data)
}

export function updateAction(id, data) {
  return api.put(`/v1/engagement/actions/${id}`, data)
}

export function approveAction(id, data = {}) {
  return api.post(`/v1/engagement/actions/${id}/approve`, data)
}

export function completeAction(id, data = {}) {
  return api.post(`/v1/engagement/actions/${id}/complete`, data)
}

export function cancelAction(id) {
  return api.post(`/v1/engagement/actions/${id}/cancel`)
}

// ============== Activities ==============

export function getContactActivities(contactId, limit = 50) {
  return api.get(`/v1/engagement/activities/contact/${contactId}`, { params: { limit } })
}

export function getEnrollmentActivities(enrollmentId) {
  return api.get(`/v1/engagement/activities/enrollment/${enrollmentId}`)
}

export function getRecentActivities(limit = 20, channel = null) {
  const params = { limit }
  if (channel) params.channel = channel
  return api.get('/v1/engagement/activities/recent', { params })
}

export function getActivity(id) {
  return api.get(`/v1/engagement/activities/${id}`)
}

export function logActivity(data) {
  return api.post('/v1/engagement/activities', data)
}

// ============== Brain API ==============

export function getAvailableChannels() {
  return api.get('/v1/engagement/brain/available-channels')
}

export function checkPrerequisites(channels) {
  return api.post('/v1/engagement/brain/check-prerequisites', { channels })
}

export function brainSetupChat(message, conversationHistory = []) {
  return api.post('/v1/engagement/brain/setup-chat', {
    message,
    conversation_history: conversationHistory
  })
}

export function generatePlaybook(config) {
  return api.post('/v1/engagement/brain/generate-playbook', config)
}

export function generateModulePrompts(config) {
  return api.post('/v1/engagement/brain/generate-module-prompts', config)
}

export function createPipelineFromSetup(config) {
  return api.post('/v1/engagement/brain/create-pipeline-from-setup', config)
}

export function analyzeContact(enrollmentId, activityIds = []) {
  return api.post('/v1/engagement/brain/analyze-contact', {
    enrollment_id: enrollmentId,
    activity_ids: activityIds
  })
}

export function analyzeResponse(enrollmentId, incomingActivityId, lastOutboundActivityId = null) {
  return api.post('/v1/engagement/brain/analyze-response', {
    enrollment_id: enrollmentId,
    incoming_activity_id: incomingActivityId,
    last_outbound_activity_id: lastOutboundActivityId
  })
}

// ============== Statistics Engine ==============

export function getStatistics(pipelineId = null, days = 30) {
  const params = { days }
  if (pipelineId) params.pipeline_id = pipelineId
  return api.get('/v1/engagement/statistics', { params })
}

export function getChannelPerformance(pipelineId = null, days = 30) {
  const params = { days }
  if (pipelineId) params.pipeline_id = pipelineId
  return api.get('/v1/engagement/statistics/channels', { params })
}

export function getConversionFunnel(pipelineId = null, days = 30) {
  const params = { days }
  if (pipelineId) params.pipeline_id = pipelineId
  return api.get('/v1/engagement/statistics/funnel', { params })
}

export function getResponseTimeAnalytics(pipelineId = null, days = 30) {
  const params = { days }
  if (pipelineId) params.pipeline_id = pipelineId
  return api.get('/v1/engagement/statistics/response-times', { params })
}

export function getOptimizationInsights(pipelineId = null, days = 90) {
  const params = { days }
  if (pipelineId) params.pipeline_id = pipelineId
  return api.get('/v1/engagement/statistics/optimization', { params })
}

// ============== A/B Testing ==============

export function getABTests(params = {}) {
  return api.get('/v1/engagement/ab-tests', { params })
}

export function getABTest(id) {
  return api.get(`/v1/engagement/ab-tests/${id}`)
}

export function createABTest(data) {
  return api.post('/v1/engagement/ab-tests', data)
}

export function updateABTest(id, data) {
  return api.put(`/v1/engagement/ab-tests/${id}`, data)
}

export function deleteABTest(id) {
  return api.delete(`/v1/engagement/ab-tests/${id}`)
}

export function startABTest(id) {
  return api.post(`/v1/engagement/ab-tests/${id}/start`)
}

export function pauseABTest(id) {
  return api.post(`/v1/engagement/ab-tests/${id}/pause`)
}

export function completeABTest(id, winnerVariantId = null) {
  const payload = winnerVariantId ? { winner_variant_id: winnerVariantId } : {}
  return api.post(`/v1/engagement/ab-tests/${id}/complete`, payload)
}

export function getABTestResults(id) {
  return api.get(`/v1/engagement/ab-tests/${id}/results`)
}

// ============== Tracking Links ==============

export function getTrackingLinks(params = {}) {
  return api.get('/v1/engagement/tracking/links', { params })
}

export function createTrackingLink(data) {
  return api.post('/v1/engagement/tracking/links', data)
}

export function createTrackingLinksBulk(data) {
  return api.post('/v1/engagement/tracking/links/bulk', data)
}

export function deactivateTrackingLink(id) {
  return api.post(`/v1/engagement/tracking/links/${id}/deactivate`)
}

// ============== Tracking Events ==============

export function getTrackingEvents(params = {}) {
  return api.get('/v1/engagement/tracking/events', { params })
}

export function getEventSummary(params = {}) {
  return api.get('/v1/engagement/tracking/events/summary', { params })
}

export function getPixelCode() {
  return api.get('/v1/engagement/tracking/pixel-code')
}

// ============== Attribution ==============

export function recordConversion(data) {
  return api.post('/v1/engagement/tracking/conversions', data)
}

export function getAttributionDashboard(params = {}) {
  return api.get('/v1/engagement/tracking/attribution', { params })
}

// ─── Pipeline Prompts (per-pipeline channel-specific LLM prompts) ───
export function listPipelinePrompts(pipelineId) {
  return api.get(`/v1/engagement/pipelines/${pipelineId}/prompts`)
}

export function createPipelinePrompt(pipelineId, data) {
  return api.post(`/v1/engagement/pipelines/${pipelineId}/prompts`, data)
}

export function updatePipelinePrompt(pipelineId, promptId, data) {
  return api.put(`/v1/engagement/pipelines/${pipelineId}/prompts/${promptId}`, data)
}

export function deletePipelinePrompt(pipelineId, promptId) {
  return api.delete(`/v1/engagement/pipelines/${pipelineId}/prompts/${promptId}`)
}

export function testPipelinePrompt(pipelineId, promptId, payload) {
  return api.post(`/v1/engagement/pipelines/${pipelineId}/prompts/${promptId}/test`, payload)
}

// ─── Bulk Brain-Run ─────────────────────────────────────────────────
export function triggerBulkBrain(pipelineId, payload) {
  return api.post(`/v1/engagement/pipelines/${pipelineId}/brain/run-bulk`, payload || {})
}

export function triggerAbBrain(pipelineId, payload) {
  return api.post(`/v1/engagement/pipelines/${pipelineId}/brain/run-ab`, payload || {})
}

export function getBulkBrainStatus(pipelineId) {
  return api.get(`/v1/engagement/pipelines/${pipelineId}/brain/status`)
}

export function stopBulkBrain(pipelineId) {
  return api.post(`/v1/engagement/pipelines/${pipelineId}/brain/stop`)
}

export function bulkDeleteActions(actionIds) {
  return api.post('/v1/engagement/actions/bulk/delete', { action_ids: actionIds })
}

export function deleteAllDrafts(pipelineId, channel = 'email') {
  return api.delete(`/v1/engagement/pipelines/${pipelineId}/drafts`, { params: { channel } })
}

// ─── Drafts (per pipeline) ───────────────────────────────────────────
export function listDrafts(pipelineId, channel = 'email') {
  return api.get(`/v1/engagement/pipelines/${pipelineId}/drafts`, { params: { channel } })
}

export function previewAction(actionId) {
  return api.get(`/v1/engagement/actions/${actionId}/preview`)
}

export function bulkApproveActions(actionIds) {
  return api.post('/v1/engagement/actions/bulk/approve', { action_ids: actionIds })
}

export function bulkRegenerateActions(actionIds, modelOverride = null) {
  return api.post('/v1/engagement/actions/bulk/regenerate', {
    action_ids: actionIds,
    model_override: modelOverride,
  })
}

export function regenerateAction(actionId, modelOverride = null) {
  const params = modelOverride ? { model_override: modelOverride } : {}
  return api.post(`/v1/engagement/actions/${actionId}/regenerate`, null, { params })
}

export function massReplaceInDrafts(pipelineId, payload) {
  return api.post(`/v1/engagement/pipelines/${pipelineId}/drafts/mass-replace`, payload)
}
