/**
 * Navigation trail store — drives the global breadcrumb component.
 *
 * Instead of building the breadcrumb hierarchically from route.meta.parent
 * (which loses context when the user navigates *across* modules — e.g.
 * Engagement → Pipeline → Contact → Company), we record the path the user
 * actually took and render it as the breadcrumb.
 *
 * The router pushes the *previous* route (`from`) onto the trail every
 * time it navigates. The current route is rendered as the last,
 * non-clickable crumb.
 *
 * Backward navigation (browser back, or click on a trail crumb): we trim
 * the trail back to that point so it doesn't keep growing.
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'

const MAX_TRAIL = 6

function makeCrumb(route) {
  if (!route || !route.fullPath) return null
  const meta = route.meta || {}
  const breadcrumb = meta.breadcrumb || {}
  const label =
    breadcrumb.label || meta.title || route.name || route.path
  return {
    name: route.name,
    path: route.fullPath,
    label,
  }
}

export const useNavStore = defineStore('nav', () => {
  // Past routes the user passed through, in order. Does NOT include the
  // current route — that's rendered separately by the breadcrumb.
  const trail = ref([])

  /**
   * Called from router.beforeEach. Push `from` onto the trail, but be
   * smart about it:
   * - skip the very first navigation (from has no name)
   * - if the user navigated back to a page already in the trail, trim
   *   instead of pushing
   * - dedupe same path consecutive entries
   */
  function recordTransition(from, to) {
    const fromCrumb = makeCrumb(from)
    if (!fromCrumb || !fromCrumb.name) return

    // Backward navigation: did we navigate to a page already in the trail?
    const idx = trail.value.findIndex((c) => c.path === to.fullPath)
    if (idx >= 0) {
      trail.value = trail.value.slice(0, idx)
      return
    }

    // Skip if same path as last entry
    const last = trail.value[trail.value.length - 1]
    if (last && last.path === fromCrumb.path) return

    trail.value.push(fromCrumb)
    // Cap at MAX_TRAIL — drop oldest when overflowing.
    if (trail.value.length > MAX_TRAIL) {
      trail.value = trail.value.slice(-MAX_TRAIL)
    }
  }

  /**
   * Trim trail to the given index (exclusive). Used by the breadcrumb
   * component when the user clicks a trail crumb.
   */
  function trimTo(index) {
    trail.value = trail.value.slice(0, index)
  }

  function reset() {
    trail.value = []
  }

  return { trail, recordTransition, trimTo, reset }
})
