/**
 * AI Setup API - prompts, context, and onboarding
 */
import api from './index'

// ═══════════════════════════════════════════════════════════════════════════════
// Module Context
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Get the context (extracted parameters) for a module
 */
export function getModuleContext(module) {
  return api.get(`/v1/ai/modules/${module}/context`)
}

/**
 * Get canonical config for a module
 */
export function getModuleConfig(module) {
  return api.get(`/v1/ai/modules/${module}/config`)
}

/**
 * Update canonical config for a module
 */
export function updateModuleConfig(module, data) {
  return api.put(`/v1/ai/modules/${module}/config`, data)
}

/**
 * Update the context for a module
 */
export function updateModuleContext(module, data) {
  return api.put(`/v1/ai/modules/${module}/context`, data)
}

/**
 * Set a single variable in module context
 */
export function setContextVariable(module, key, value) {
  return api.put(`/v1/ai/modules/${module}/context/variable`, { key, value })
}

/**
 * Delete a variable from module context
 */
export function deleteContextVariable(module, key) {
  return api.delete(`/v1/ai/modules/${module}/context/variable`, { data: { key } })
}

// ═══════════════════════════════════════════════════════════════════════════════
// Module Parameters
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Get all parameters for a module
 */
export function getModuleParameters(module) {
  return api.get(`/v1/ai/modules/${module}/parameters`)
}

/**
 * Create a new parameter
 */
export function createParameter(module, data) {
  return api.post(`/v1/ai/modules/${module}/parameters`, data)
}

/**
 * Update a parameter
 */
export function updateParameter(module, variable, data) {
  return api.put(`/v1/ai/modules/${module}/parameters/${variable}`, data)
}

/**
 * Set just the value of a parameter
 */
export function setParameterValue(module, variable, value) {
  return api.patch(`/v1/ai/modules/${module}/parameters/${variable}/value`, { value })
}

/**
 * Delete a parameter
 */
export function deleteParameter(module, variable) {
  return api.delete(`/v1/ai/modules/${module}/parameters/${variable}`)
}

/**
 * Reorder parameters
 */
export function reorderParameters(module, order) {
  return api.put(`/v1/ai/modules/${module}/parameters/reorder`, order)
}

// ═══════════════════════════════════════════════════════════════════════════════
// Prompts
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Get all prompts for a module, grouped by type (setup/productive)
 */
export function getModulePrompts(module) {
  return api.get(`/v1/ai/modules/${module}/prompts`)
}

/**
 * Get a specific prompt by slug
 */
export function getPrompt(module, slug) {
  return api.get(`/v1/ai/modules/${module}/prompts/${slug}`)
}

/**
 * Create a new prompt for a module
 */
export function createPrompt(module, data) {
  return api.post(`/v1/ai/modules/${module}/prompts`, data)
}

/**
 * Update an existing prompt
 */
export function updatePrompt(module, promptId, data) {
  return api.put(`/v1/ai/modules/${module}/prompts/${promptId}`, data)
}

/**
 * Delete a prompt (soft delete)
 */
export function deletePrompt(module, promptId) {
  return api.delete(`/v1/ai/modules/${module}/prompts/${promptId}`)
}

/**
 * Reorder prompts
 */
export function reorderPrompts(module, promptType, order) {
  return api.put(`/v1/ai/modules/${module}/prompts/reorder/${promptType}`, order)
}

// ═══════════════════════════════════════════════════════════════════════════════
// Onboarding
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Start an onboarding conversation for a module
 */
export function startOnboarding(module) {
  return api.post(`/v1/ai/modules/${module}/onboarding/start`)
}

/**
 * Continue an onboarding conversation
 */
export function sendOnboardingMessage(module, conversationId, message) {
  return api.post(`/v1/ai/modules/${module}/onboarding/${conversationId}/chat`, {
    message
  })
}

/**
 * Reset onboarding for a module (clears context and status)
 */
export function resetOnboarding(module) {
  return api.post(`/v1/ai/modules/${module}/onboarding/reset`)
}

// ═══════════════════════════════════════════════════════════════════════════════
// Prompt Rendering (for preview/testing)
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Render a prompt with context variables substituted
 */
export function renderPrompt(module, slug, extraVars = {}) {
  return api.post(`/v1/ai/modules/${module}/prompts/${slug}/render`, extraVars)
}

export default {
  getModuleContext,
  getModuleConfig,
  updateModuleContext,
  updateModuleConfig,
  setContextVariable,
  deleteContextVariable,
  getModuleParameters,
  createParameter,
  updateParameter,
  setParameterValue,
  deleteParameter,
  reorderParameters,
  getModulePrompts,
  getPrompt,
  createPrompt,
  updatePrompt,
  deletePrompt,
  reorderPrompts,
  startOnboarding,
  sendOnboardingMessage,
  resetOnboarding,
  renderPrompt
}
