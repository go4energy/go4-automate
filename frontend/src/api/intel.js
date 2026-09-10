/**
 * Intel API client — wraps /api/v1/intel/*.
 *
 * Tenant header is added globally by api/index.js axios interceptor.
 * axios.baseURL is "/api", so paths here are prefixed with "/v1/".
 */
import api from '@/api'

export const intelApi = {
  // ── Watch Targets ─────────────────────────────────────────────
  listTargets() {
    return api.get('/v1/intel/targets').then((r) => r.data)
  },
  getTarget(id) {
    return api.get(`/v1/intel/targets/${id}`).then((r) => r.data)
  },
  createTarget(payload) {
    return api.post('/v1/intel/targets', payload).then((r) => r.data)
  },
  updateTarget(id, payload) {
    return api.put(`/v1/intel/targets/${id}`, payload).then((r) => r.data)
  },
  deleteTarget(id) {
    return api.delete(`/v1/intel/targets/${id}`).then((r) => r.data)
  },

  // ── Sources ───────────────────────────────────────────────────
  listSources(targetId) {
    return api.get(`/v1/intel/targets/${targetId}/sources`).then((r) => r.data)
  },
  createSource(targetId, payload) {
    return api.post(`/v1/intel/targets/${targetId}/sources`, payload).then((r) => r.data)
  },
  updateSource(sourceId, payload) {
    return api.put(`/v1/intel/sources/${sourceId}`, payload).then((r) => r.data)
  },
  deleteSource(sourceId) {
    return api.delete(`/v1/intel/sources/${sourceId}`).then((r) => r.data)
  },

  // ── Briefings ─────────────────────────────────────────────────
  listBriefings({ limit = 30, offset = 0 } = {}) {
    return api.get('/v1/intel/briefings', { params: { limit, offset } }).then((r) => r.data)
  },
  getBriefing(id) {
    return api.get(`/v1/intel/briefings/${id}`).then((r) => r.data)
  },

  // ── Events ────────────────────────────────────────────────────
  listEvents(params = {}) {
    return api.get('/v1/intel/events', { params }).then((r) => r.data)
  },

  // ── Admin ─────────────────────────────────────────────────────
  embedHealth() {
    return api.get('/v1/intel/admin/embed-health').then((r) => r.data)
  },
  runNow() {
    return api.post('/v1/intel/admin/run-now').then((r) => r.data)
  }
}
