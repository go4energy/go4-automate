/**
 * Meta Conversions API Client
 *
 * API client for Meta (Facebook) Conversions API integration.
 * Handles setup, configuration, event sending, and statistics.
 */

import api from '@/api'

const BASE = '/v1/engagement/meta'

// ============== Status ==============

/**
 * Get quick status of Meta integration.
 * @returns {Promise<{is_configured, is_active, test_mode, pixel_id, last_event_at, events_today, success_rate}>}
 */
export function getMetaStatus() {
  return api.get(`${BASE}/status`)
}

// ============== Integration CRUD ==============

/**
 * Get current Meta integration configuration.
 * Returns null if not configured.
 * @returns {Promise<MetaIntegration|null>}
 */
export function getMetaIntegration() {
  return api.get(`${BASE}/integration`)
}

/**
 * Create or update Meta integration.
 * @param {Object} data - Integration configuration
 * @param {string} data.pixel_id - Meta Pixel ID (15-16 digits)
 * @param {string} data.access_token - System User access token
 * @param {string} [data.ad_account_id] - Optional Ad Account ID
 * @param {boolean} [data.is_active=true] - Enable/disable integration
 * @param {boolean} [data.test_mode=false] - Send test events
 * @returns {Promise<MetaIntegration>}
 */
export function createMetaIntegration(data) {
  return api.post(`${BASE}/integration`, data)
}

/**
 * Update existing Meta integration.
 * Only provided fields will be updated.
 * @param {Object} data - Fields to update
 * @returns {Promise<MetaIntegration>}
 */
export function updateMetaIntegration(data) {
  return api.put(`${BASE}/integration`, data)
}

/**
 * Deactivate Meta integration (soft delete).
 * @returns {Promise<void>}
 */
export function deleteMetaIntegration() {
  return api.delete(`${BASE}/integration`)
}

// ============== Test Event ==============

/**
 * Send a test event to verify integration.
 * @param {Object} params - Test event parameters
 * @param {string} [params.event_name='PageView'] - Event type to test
 * @param {number} [params.contact_id] - Optional contact to use
 * @param {string} [params.url] - Optional URL for PageView
 * @returns {Promise<{success, event_id, message, response_body}>}
 */
export function sendTestEvent(params = {}) {
  return api.post(`${BASE}/test-event`, params)
}

// ============== Events ==============

/**
 * Get paginated list of conversion events.
 * @param {Object} params - Query parameters
 * @param {number} [params.page=1] - Page number
 * @param {number} [params.page_size=50] - Items per page
 * @param {string} [params.status] - Filter by status (sent, failed, test)
 * @param {string} [params.event_name] - Filter by event name
 * @param {number} [params.contact_id] - Filter by contact
 * @param {number} [params.days] - Filter to last N days
 * @returns {Promise<{items, total, page, page_size}>}
 */
export function getConversionEvents(params = {}) {
  return api.get(`${BASE}/events`, { params })
}

/**
 * Get details of a specific conversion event.
 * @param {number} eventId - Event database ID
 * @returns {Promise<ConversionEvent>}
 */
export function getConversionEvent(eventId) {
  return api.get(`${BASE}/events/${eventId}`)
}

// ============== Statistics ==============

/**
 * Get event statistics for the specified period.
 * @param {number} [days=7] - Number of days to include
 * @returns {Promise<{period_start, period_end, total_events, events_sent, events_failed, success_rate, events_by_type, events_by_day}>}
 */
export function getMetaStats(days = 7) {
  return api.get(`${BASE}/stats`, { params: { days } })
}

// ============== Setup Guide ==============

/**
 * Get step-by-step setup instructions.
 * @returns {Promise<{steps: Array}>}
 */
export function getSetupGuide() {
  return api.get(`${BASE}/setup-guide`)
}
