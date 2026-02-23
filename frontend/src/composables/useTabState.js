import { ref, watch } from 'vue'

const STORAGE_PREFIX = 'tab_'

/**
 * Persists the active tab in sessionStorage so it survives navigation.
 * @param {string} key - Unique key per view (e.g. 'collector', 'user-management')
 * @param {string} defaultTab - Fallback if nothing stored
 * @param {string[]} validTabs - Allowed tab keys (guards against stale values)
 */
export function useTabState(key, defaultTab, validTabs = []) {
  const storageKey = STORAGE_PREFIX + key
  const stored = sessionStorage.getItem(storageKey)
  const initial =
    stored && (validTabs.length === 0 || validTabs.includes(stored)) ? stored : defaultTab

  const activeTab = ref(initial)

  watch(activeTab, (val) => {
    sessionStorage.setItem(storageKey, val)
  })

  return activeTab
}
