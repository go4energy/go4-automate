import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import {
  getModules,
  getModuleSchema,
  getModuleConfig,
  updateModuleConfig,
  getModuleStatus,
  getGlobalSchema,
  getGlobalConfig,
  updateGlobalConfig
} from '@/api/settings'

export const useSettingsStore = defineStore('settings', () => {
  // State
  const modules = ref([])
  const activeTab = ref('global')
  const schemas = ref({})
  const configs = ref({})
  const statuses = ref({})
  const globalSchema = ref(null)
  const globalConfig = ref({})
  const loading = ref(false)
  const saving = ref(false)
  const error = ref(null)
  const saveSuccess = ref(false)

  // Computed
  const tabs = computed(() => {
    const list = [{ key: 'global', label: 'Plattform' }]
    for (const mod of modules.value) {
      list.push({ key: mod.name, label: mod.label })
    }
    return list
  })

  // Actions
  async function fetchModules() {
    loading.value = true
    error.value = null
    try {
      const { data } = await getModules()
      modules.value = data
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function fetchTabData(tab) {
    loading.value = true
    error.value = null
    try {
      if (tab === 'global') {
        const [schemaRes, configRes] = await Promise.all([getGlobalSchema(), getGlobalConfig()])
        globalSchema.value = schemaRes.data
        globalConfig.value = configRes.data.config || {}
      } else {
        const [schemaRes, configRes, statusRes] = await Promise.all([
          getModuleSchema(tab),
          getModuleConfig(tab),
          getModuleStatus(tab)
        ])
        schemas.value[tab] = schemaRes.data
        configs.value[tab] = configRes.data.config || {}
        statuses.value[tab] = statusRes.data
      }
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function saveModuleConfig(name, updates) {
    saving.value = true
    error.value = null
    saveSuccess.value = false
    try {
      const { data } = await updateModuleConfig(name, updates)
      configs.value[name] = data.config || {}
      saveSuccess.value = true
      setTimeout(() => {
        saveSuccess.value = false
      }, 3000)
    } catch (err) {
      error.value = err.message
    } finally {
      saving.value = false
    }
  }

  async function saveGlobalSettings(updates) {
    saving.value = true
    error.value = null
    saveSuccess.value = false
    try {
      const { data } = await updateGlobalConfig(updates)
      globalConfig.value = data.config || {}
      saveSuccess.value = true
      setTimeout(() => {
        saveSuccess.value = false
      }, 3000)
    } catch (err) {
      error.value = err.message
    } finally {
      saving.value = false
    }
  }

  function setActiveTab(tab) {
    activeTab.value = tab
    saveSuccess.value = false
    error.value = null
  }

  return {
    modules,
    activeTab,
    schemas,
    configs,
    statuses,
    globalSchema,
    globalConfig,
    loading,
    saving,
    error,
    saveSuccess,
    tabs,
    fetchModules,
    fetchTabData,
    saveModuleConfig,
    saveGlobalSettings,
    setActiveTab
  }
})
