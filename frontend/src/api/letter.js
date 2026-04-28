/**
 * Letter API Client
 *
 * Physische Briefe als Engagement-Kanal
 */

import api from './index'

const BASE_URL = '/letter'

// ============== Templates ==============

/**
 * List all templates
 * @param {Object} params - Query params (skip, limit, active_only)
 */
export async function getTemplates(params = {}) {
  const { data } = await api.get(`${BASE_URL}/templates`, { params })
  return data
}

/**
 * Get template by ID
 * @param {number} id - Template ID
 */
export async function getTemplate(id) {
  const { data } = await api.get(`${BASE_URL}/templates/${id}`)
  return data
}

/**
 * Create new template
 * @param {Object} template - Template data
 */
export async function createTemplate(template) {
  const { data } = await api.post(`${BASE_URL}/templates`, template)
  return data
}

/**
 * Update template
 * @param {number} id - Template ID
 * @param {Object} template - Template data
 */
export async function updateTemplate(id, template) {
  const { data } = await api.put(`${BASE_URL}/templates/${id}`, template)
  return data
}

/**
 * Delete template
 * @param {number} id - Template ID
 */
export async function deleteTemplate(id) {
  await api.delete(`${BASE_URL}/templates/${id}`)
}

/**
 * Preview template rendering
 * @param {Object} params - { template_id, contact_id?, custom_data? }
 */
export async function previewTemplate(params) {
  const { data } = await api.post(`${BASE_URL}/templates/preview`, params)
  return data
}

// ============== Letters ==============

/**
 * List all letters
 * @param {Object} params - Query params (skip, limit, status, contact_id, batch_id)
 */
export async function getLetters(params = {}) {
  const { data } = await api.get(`${BASE_URL}/letters`, { params })
  return data
}

/**
 * Get letter by ID
 * @param {number} id - Letter ID
 */
export async function getLetter(id) {
  const { data } = await api.get(`${BASE_URL}/letters/${id}`)
  return data
}

/**
 * Create new letter
 * @param {Object} letter - Letter data { template_id, contact_id?, recipient, content_html? }
 */
export async function createLetter(letter) {
  const { data } = await api.post(`${BASE_URL}/letters`, letter)
  return data
}

/**
 * Create letter from pending action
 * @param {Object} params - { pending_action_id, template_id }
 */
export async function createLetterFromAction(params) {
  const { data } = await api.post(`${BASE_URL}/letters/from-action`, params)
  return data
}

/**
 * Update letter
 * @param {number} id - Letter ID
 * @param {Object} letter - Letter data
 */
export async function updateLetter(id, letter) {
  const { data } = await api.put(`${BASE_URL}/letters/${id}`, letter)
  return data
}

/**
 * Delete letter
 * @param {number} id - Letter ID
 */
export async function deleteLetter(id) {
  await api.delete(`${BASE_URL}/letters/${id}`)
}

/**
 * Approve letter (set status to approved)
 * @param {number} id - Letter ID
 */
export async function approveLetter(id) {
  const { data } = await api.post(`${BASE_URL}/letters/${id}/approve`)
  return data
}

/**
 * Generate PDF for letter
 * @param {number} id - Letter ID
 */
export async function generateLetterPdf(id) {
  const { data } = await api.post(`${BASE_URL}/letters/${id}/generate-pdf`)
  return data
}

// ============== Batches ==============

/**
 * List all batches
 * @param {Object} params - Query params (skip, limit, status)
 */
export async function getBatches(params = {}) {
  const { data } = await api.get(`${BASE_URL}/batches`, { params })
  return data
}

/**
 * Get batch by ID
 * @param {number} id - Batch ID
 */
export async function getBatch(id) {
  const { data } = await api.get(`${BASE_URL}/batches/${id}`)
  return data
}

/**
 * Create new batch
 * @param {Object} batch - { name, letter_ids }
 */
export async function createBatch(batch) {
  const { data } = await api.post(`${BASE_URL}/batches`, batch)
  return data
}

/**
 * Update batch
 * @param {number} id - Batch ID
 * @param {Object} batch - Batch data
 */
export async function updateBatch(id, batch) {
  const { data } = await api.put(`${BASE_URL}/batches/${id}`, batch)
  return data
}

/**
 * Export batch (generate CSV)
 * @param {number} id - Batch ID
 */
export async function exportBatch(id) {
  const { data } = await api.post(`${BASE_URL}/batches/${id}/export`)
  return data
}

/**
 * Mark batch as sent
 * @param {number} id - Batch ID
 */
export async function markBatchSent(id) {
  const { data } = await api.post(`${BASE_URL}/batches/${id}/mark-sent`)
  return data
}

// ============== Stats ==============

/**
 * Get letter statistics
 */
export async function getStats() {
  const { data } = await api.get(`${BASE_URL}/stats`)
  return data
}

export default {
  // Templates
  getTemplates,
  getTemplate,
  createTemplate,
  updateTemplate,
  deleteTemplate,
  previewTemplate,
  // Letters
  getLetters,
  getLetter,
  createLetter,
  createLetterFromAction,
  updateLetter,
  deleteLetter,
  approveLetter,
  generateLetterPdf,
  // Batches
  getBatches,
  getBatch,
  createBatch,
  updateBatch,
  exportBatch,
  markBatchSent,
  // Stats
  getStats,
}
