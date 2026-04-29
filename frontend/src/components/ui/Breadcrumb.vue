<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useNavStore } from '@/stores/nav'

const route = useRoute()
const router = useRouter()
const navStore = useNavStore()

// Trail-driven breadcrumb: shows the actual path the user took (not
// the manifest's hierarchical parent chain). Lets the user jump back
// to any previous step. The current page is always the last,
// non-clickable crumb.
const breadcrumbs = computed(() => {
  const crumbs = [{ label: 'Home', to: '/', isLast: false }]

  for (let i = 0; i < navStore.trail.length; i++) {
    const item = navStore.trail[i]
    crumbs.push({
      label: item.label,
      to: item.path,
      trailIndex: i,
      isLast: false,
    })
  }

  // Current page (active)
  const meta = route.meta || {}
  const breadcrumbMeta = meta.breadcrumb || {}
  const currentLabel =
    breadcrumbMeta.label || meta.title || route.name || route.path
  crumbs.push({
    label: currentLabel,
    to: null,
    isLast: true,
  })

  return crumbs
})

function navigateTo(crumb) {
  if (!crumb.to) return
  // When the user clicks a trail crumb, trim the trail to that point so
  // it doesn't look like they're moving forward into something they
  // already visited.
  if (typeof crumb.trailIndex === 'number') {
    navStore.trimTo(crumb.trailIndex)
  } else if (crumb.to === '/') {
    navStore.reset()
  }
  router.push(crumb.to)
}
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

        <!-- Clickable crumb -->
        <button
          v-if="crumb.to && !crumb.isLast"
          type="button"
          class="hover:text-gray-700 hover:underline transition-colors"
          @click="navigateTo(crumb)"
        >
          {{ crumb.label }}
        </button>
        <!-- Current (last) -->
        <span
          v-else
          class="text-gray-900 dark:text-gray-100 font-medium"
        >
          {{ crumb.label }}
        </span>
      </li>
    </ol>
  </nav>
</template>
