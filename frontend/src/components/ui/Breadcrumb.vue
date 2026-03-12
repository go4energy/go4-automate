<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

// Build breadcrumb trail from current route and its parents
const breadcrumbs = computed(() => {
  const crumbs = []

  // Always start with Home
  crumbs.push({
    label: 'Home',
    to: '/',
    isLast: false
  })

  // Build trail from route meta
  const buildTrail = (routeName) => {
    const matchedRoute = router.getRoutes().find((r) => r.name === routeName)
    if (!matchedRoute) return

    const meta = matchedRoute.meta || {}
    const breadcrumb = meta.breadcrumb || {}

    // First, add parent if exists
    if (breadcrumb.parent) {
      buildTrail(breadcrumb.parent)
    }

    // Then add this route
    const label = breadcrumb.label || meta.title || routeName
    crumbs.push({
      label,
      to: matchedRoute.path.includes(':') ? null : { name: routeName },
      isLast: false
    })
  }

  // Start building from current route
  if (route.name) {
    buildTrail(route.name)
  }

  // Mark the last one
  if (crumbs.length > 0) {
    crumbs[crumbs.length - 1].isLast = true
  }

  return crumbs
})
</script>

<template>
  <nav
    class="flex items-center text-sm text-gray-500 mb-4"
    aria-label="Breadcrumb"
  >
    <ol class="flex items-center space-x-2">
      <li
        v-for="(crumb, index) in breadcrumbs"
        :key="index"
        class="flex items-center"
      >
        <!-- Separator -->
        <svg
          v-if="index > 0"
          class="h-4 w-4 text-gray-400 mx-2"
          fill="currentColor"
          viewBox="0 0 20 20"
        >
          <path
            fill-rule="evenodd"
            d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
            clip-rule="evenodd"
          />
        </svg>

        <!-- Crumb -->
        <router-link
          v-if="crumb.to && !crumb.isLast"
          :to="crumb.to"
          class="hover:text-gray-700 hover:underline transition-colors"
        >
          {{ crumb.label }}
        </router-link>
        <span
          v-else
          class="text-gray-900 font-medium"
        >
          {{ crumb.label }}
        </span>
      </li>
    </ol>
  </nav>
</template>
