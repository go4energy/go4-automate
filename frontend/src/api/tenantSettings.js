/**
 * Tenant-Stammdaten API client.
 *
 * Quelle für rechtskonforme Email-Footer (Impressum, Disclaimer) und
 * Compliance-Felder (Datenschutz-URL, Test-Empfänger).
 */
import api from '@/api'

export function getTenantMasterData() {
  return api.get('/v1/tenant-settings/master-data')
}

export function updateTenantMasterData(payload) {
  return api.put('/v1/tenant-settings/master-data', payload)
}

export function previewImpressum() {
  return api.get('/v1/tenant-settings/preview-impressum')
}

export function previewDisclaimer() {
  return api.get('/v1/tenant-settings/preview-disclaimer')
}
