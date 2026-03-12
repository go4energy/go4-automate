import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { getModules, getDesktopModules } from '@/api/modules'

export const useModuleStore = defineStore('modules', () => {
  const modules = ref([])
  const desktopModules = ref([])
  const loading = ref(false)
  const error = ref(null)

  // Flat sorted list — no category grouping, backend already sorts by order
  const desktopSorted = computed(() => {
    return [...desktopModules.value].sort((a, b) => (a.order || 99) - (b.order || 99))
  })

  // Keep for backwards compat (sidebar etc.)
  const desktopGrouped = computed(() => {
    const groups = {}
    for (const mod of desktopModules.value) {
      const cat = mod.category || 'system'
      if (!groups[cat]) groups[cat] = []
      groups[cat].push(mod)
    }
    return groups
  })

  const appModules = computed(() => modules.value.filter((m) => m.application))

  // Group ordering: SALES + MARKETING first, SYSTEM + TOOLS last
  const groupOrder = ['SALES', 'MARKETING', 'CONTENT', 'VERWALTUNG', 'SYSTEM', 'TOOLS']

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
    // Sort groups by predefined order
    const sortedGroups = Object.entries(groups)
      .map(([label, items]) => ({
        label,
        items: items.sort((a, b) => a.order - b.order)
      }))
      .sort((a, b) => {
        const aIdx = groupOrder.indexOf(a.label)
        const bIdx = groupOrder.indexOf(b.label)
        if (aIdx === -1 && bIdx === -1) return a.label.localeCompare(b.label)
        if (aIdx === -1) return 1
        if (bIdx === -1) return -1
        return aIdx - bIdx
      })
    return sortedGroups
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
    desktopSorted,
    desktopGrouped,
    appModules,
    sidebarGroups,
    fetchModules,
    fetchDesktop
  }
})
