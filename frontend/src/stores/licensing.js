import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { getEnabledModules, getLicenses, grantLicense, revokeLicense } from '@/api/licensing'

/**
 * Pinia store for per-tenant module licensing.
 *
 * Permissive contract: when the backend returns `permissive=true` (= the
 * tenant has no license rows yet), every module is treated as enabled.
 * This is the default for legacy / un-licensed tenants and keeps the UI
 * working unchanged.
 *
 * `isModuleEnabled(key)` is the single source of truth for sidebar
 * filtering and route guards.
 */
export const useLicensingStore = defineStore('licensing', () => {
  const enabled = ref([])      // list of module keys, or ["*"] in permissive mode
  const permissive = ref(true) // legacy default
  const licenses = ref([])     // detailed license rows (Settings UI)
  const loading = ref(false)
  const error = ref(null)
  const loaded = ref(false)

  const isModuleEnabled = computed(() => (key) => {
    if (permissive.value) return true
    return enabled.value.includes(key)
  })

  async function fetchEnabled() {
    loading.value = true
    error.value = null
    try {
      const { data } = await getEnabledModules()
      enabled.value = data.enabled || []
      permissive.value = !!data.permissive
      loaded.value = true
    } catch (err) {
      // Soft-fail: if the licensing endpoint is unreachable, keep the
      // permissive default so the UI doesn't lock the user out.
      error.value = err.message
      enabled.value = []
      permissive.value = true
    } finally {
      loading.value = false
    }
  }

  async function fetchLicenses() {
    loading.value = true
    error.value = null
    try {
      const { data } = await getLicenses()
      licenses.value = data
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function grant(payload) {
    const { data } = await grantLicense(payload)
    await fetchLicenses()
    await fetchEnabled()
    return data
  }

  async function revoke(moduleKey) {
    await revokeLicense(moduleKey)
    await fetchLicenses()
    await fetchEnabled()
  }

  return {
    enabled,
    permissive,
    licenses,
    loading,
    error,
    loaded,
    isModuleEnabled,
    fetchEnabled,
    fetchLicenses,
    grant,
    revoke
  }
})
