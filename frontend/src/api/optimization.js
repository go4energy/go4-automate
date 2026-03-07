/**
 * Optimization Engine API Client
 *
 * API client for pipeline optimization analysis.
 * Handles report generation, insights, and statistics.
 */

import api from '@/api'

const BASE = '/v1/engagement/optimization'

// ============== Analysis ==============

/**
 * Analyze a pipeline for optimization opportunities.
 * @param {number} pipelineId - Pipeline to analyze
 * @param {Object} params - Analysis parameters
 * @param {string} [params.report_type='ad_hoc'] - Type of report
 * @param {number} [params.days=30] - Days to analyze
 * @returns {Promise<OptimizationReport>}
 */
export function analyzePipeline(pipelineId, params = {}) {
  return api.post(`${BASE}/pipelines/${pipelineId}/analyze`, {
    report_type: params.report_type || 'ad_hoc',
    days: params.days || 30
  })
}

// ============== Reports ==============

/**
 * List optimization reports.
 * @param {Object} params - Query parameters
 * @param {number} [params.pipeline_id] - Filter by pipeline
 * @param {number} [params.limit=20] - Max results
 * @param {number} [params.offset=0] - Skip count
 * @returns {Promise<{items, total}>}
 */
export function listReports(params = {}) {
  return api.get(`${BASE}/reports`, { params })
}

/**
 * Get a detailed optimization report.
 * @param {number} reportId - Report ID
 * @returns {Promise<OptimizationReportDetail>}
 */
export function getReport(reportId) {
  return api.get(`${BASE}/reports/${reportId}`)
}

/**
 * Apply recommendations from a report.
 * @param {number} reportId - Report ID
 * @returns {Promise<{success, message, pipeline_id}>}
 */
export function applyRecommendations(reportId) {
  return api.post(`${BASE}/reports/${reportId}/apply`)
}

// ============== Insights ==============

/**
 * List optimization insights.
 * @param {Object} params - Query parameters
 * @param {number} [params.report_id] - Filter by report
 * @param {string} [params.insight_type] - Filter by type
 * @param {string} [params.priority] - Filter by priority
 * @param {number} [params.limit=50] - Max results
 * @returns {Promise<{items, total}>}
 */
export function listInsights(params = {}) {
  return api.get(`${BASE}/insights`, { params })
}

// ============== Stats ==============

/**
 * Get optimization statistics.
 * @returns {Promise<OptimizationStats>}
 */
export function getOptimizationStats() {
  return api.get(`${BASE}/stats`)
}
