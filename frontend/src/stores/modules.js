import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { getModules, getDesktopModules } from '@/api/modules'

export const useModuleStore = defineStore('modules', () => {
  const modules = ref([])
  const desktopModules = ref([])
  const loading = ref(false)
  const error = ref(null)

  const desktopGrouped = computed(() => {
    const groups = {}
    for (const mod of desktopModules.value) {
      const cat = mod.category || 'system'
      if (!groups[cat]) groups[cat] = []
      groups[cat].push(mod)
    }
    // Ensure marketing comes first, then system
    const ordered = {}
    if (groups.marketing) ordered.marketing = groups.marketing
    for (const [key, val] of Object.entries(groups)) {
      if (key !== 'marketing') ordered[key] = val
    }
    return ordered
  })

  const appModules = computed(() => modules.value.filter((m) => m.application))

  const sidebarGroups = computed(() => {
    const groups = {}
    for (const mod of modules.value) {
      if (!mod.sidebar) continue
      const groupLabel = mod.sidebar.group || 'SONSTIGES'
      if (!groups[groupLabel]) groups[groupLabel] = []
      groups[groupLabel].push({
        to: mod.frontend?.base_route || `/${mod.name}`,
        label: mod.label || mod.name,
        icon: mod.icon || '',
        module: mod.name,
        order: mod.sidebar.order || 99
      })
    }
    return Object.entries(groups).map(([label, items]) => ({
      label,
      items: items.sort((a, b) => a.order - b.order)
    }))
  })

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

  async function fetchDesktop() {
    loading.value = true
    error.value = null
    try {
      const { data } = await getDesktopModules()
      desktopModules.value = data
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  return {
    modules,
    desktopModules,
    loading,
    error,
    desktopGrouped,
    appModules,
    sidebarGroups,
    fetchModules,
    fetchDesktop
  }
})
