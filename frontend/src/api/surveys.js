import api from '@/api'

// ============== Surveys ==============

export function getSurveys(params = {}) {
  return api.get('/v1/surveys', { params })
}

export function getSurvey(id) {
  return api.get(`/v1/surveys/${id}`)
}

export function createSurvey(data) {
  return api.post('/v1/surveys', data)
}

export function updateSurvey(id, data) {
  return api.put(`/v1/surveys/${id}`, data)
}

export function deleteSurvey(id) {
  return api.delete(`/v1/surveys/${id}`)
}

export function updateSurveyStatus(id, status) {
  return api.patch(`/v1/surveys/${id}/status`, { status })
}

export function duplicateSurvey(id) {
  return api.post(`/v1/surveys/${id}/duplicate`)
}

// ============== Questions ==============

export function addQuestion(surveyId, data) {
  return api.post(`/v1/surveys/${surveyId}/questions`, data)
}

export function updateQuestion(questionId, data) {
  return api.put(`/v1/surveys/questions/${questionId}`, data)
}

export function deleteQuestion(questionId) {
  return api.delete(`/v1/surveys/questions/${questionId}`)
}

export function reorderQuestions(surveyId, questionIds) {
  return api.patch(`/v1/surveys/${surveyId}/questions/reorder`, { question_ids: questionIds })
}

// ============== Responses ==============

export function getResponses(surveyId, params = {}) {
  return api.get(`/v1/surveys/${surveyId}/responses`, { params })
}

export function getResponse(responseId) {
  return api.get(`/v1/surveys/responses/${responseId}`)
}

export function deleteResponse(responseId) {
  return api.delete(`/v1/surveys/responses/${responseId}`)
}

// ============== Stats ==============

export function getSurveyStats(surveyId) {
  return api.get(`/v1/surveys/${surveyId}/stats`)
}

// ============== Share / Distribution ==============

export function getShareLink(surveyId) {
  return api.get(`/v1/surveys/${surveyId}/share-link`)
}

export function getQrCodeUrl(surveyId) {
  return `/api/v1/surveys/${surveyId}/qr-code`
}

export function sendInvites(surveyId, data) {
  return api.post(`/v1/surveys/${surveyId}/send-invites`, data)
}
