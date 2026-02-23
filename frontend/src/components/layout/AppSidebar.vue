<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useLayoutStore } from '@/stores/layout'
import { useModuleStore } from '@/stores/modules'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const layout = useLayoutStore()
const moduleStore = useModuleStore()
const authStore = useAuthStore()

// Static items always present
const staticTopItems = [
  {
    to: '/',
    label: 'Desktop',
    icon: 'M2.25 12l8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25',
    group: '_top',
    order: 0
  }
]

const staticVerwaltungItems = [
  {
    href: 'https://n8n.go4.energy',
    label: 'n8n Workflows',
    icon: 'M13.5 16.875h3.375m0 0h3.375m-3.375 0V13.5m0 3.375v3.375M6 10.5h2.25a2.25 2.25 0 002.25-2.25V6a2.25 2.25 0 00-2.25-2.25H6A2.25 2.25 0 003.75 6v2.25A2.25 2.25 0 006 10.5zm0 9.75h2.25A2.25 2.25 0 0010.5 18v-2.25a2.25 2.25 0 00-2.25-2.25H6a2.25 2.25 0 00-2.25 2.25V18A2.25 2.25 0 006 20.25zm9.75-9.75H18a2.25 2.25 0 002.25-2.25V6A2.25 2.25 0 0018 3.75h-2.25A2.25 2.25 0 0013.5 6v2.25a2.25 2.25 0 002.25 2.25z',
    group: 'VERWALTUNG',
    order: 90
  }
]

const navGroups = computed(() => {
  const groups = []

  // Top group with Desktop
  groups.push({
    label: '_top',
    items: staticTopItems
  })

  // Dynamic module groups from store
  for (const group of moduleStore.sidebarGroups) {
    // Filter items by permission
    const items = group.items.filter((item) => {
      if (!item.module) return true
      return authStore.isAdmin || authStore.canViewModule(item.module)
    })

    // Inject static VERWALTUNG items
    if (group.label === 'VERWALTUNG') {
      for (const item of staticVerwaltungItems) {
        items.push(item)
      }
      items.sort((a, b) => (a.order || 99) - (b.order || 99))
    }

    if (items.length > 0) {
      groups.push({
        label: group.label,
        items
      })
    }
  }

  // If no VERWALTUNG group from modules, create one with static items only
  if (!moduleStore.sidebarGroups.find((g) => g.label === 'VERWALTUNG')) {
    groups.push({
      label: 'VERWALTUNG',
      items: [...staticVerwaltungItems]
    })
  }

  return groups
})

function isActive(item) {
  if (item.to === '/') return route.path === '/'
  return route.path.startsWith(item.to)
}

const sidebarWidth = computed(() => (layout.sidebarCollapsed ? 'w-16' : 'w-64'))

onMounted(() => {
  if (moduleStore.modules.length === 0) {
    moduleStore.fetchModules()
  }
})
</script>

<template>
  <aside
    :class="[
      sidebarWidth,
      'fixed inset-y-0 left-0 z-30 flex flex-col border-r border-gray-200 bg-white transition-all duration-200 dark:border-gray-700 dark:bg-gray-900'
    ]"
  >
    <!-- Logo -->
    <div class="flex h-16 items-center border-b border-gray-200 px-4 dark:border-gray-700">
      <div class="flex items-center gap-2 overflow-hidden">
        <div
          class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-go4-primary text-sm font-bold text-white"
        >
          g4
        </div>
        <span
          v-if="!layout.sidebarCollapsed"
          class="whitespace-nowrap text-sm font-semibold text-go4-secondary dark:text-gray-100"
        >
          go4-automate
        </span>
      </div>
    </div>

    <!-- Navigation -->
    <nav class="flex-1 overflow-y-auto px-2 py-4">
      <div v-for="group in navGroups" :key="group.label" class="mb-6">
        <p
          v-if="!layout.sidebarCollapsed && group.label !== '_top'"
          class="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-gray-400"
        >
          {{ group.label }}
        </p>
        <div class="space-y-1">
          <template v-for="item in group.items" :key="item.label">
            <!-- External link -->
            <a
              v-if="item.href"
              :href="item.href"
              target="_blank"
              :class="[
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition',
                'text-gray-600 hover:bg-gray-100 hover:text-go4-secondary dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200'
              ]"
              :title="layout.sidebarCollapsed ? item.label : undefined"
            >
              <svg
                class="h-5 w-5 shrink-0"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="1.5"
              >
                <path stroke-linecap="round" stroke-linejoin="round" :d="item.icon" />
              </svg>
              <span v-if="!layout.sidebarCollapsed" class="truncate">{{ item.label }}</span>
            </a>
            <!-- Router link -->
            <router-link
              v-else
              :to="item.to"
              :class="[
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition',
                isActive(item)
                  ? 'bg-go4-primary/10 text-go4-primary'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-go4-secondary dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200'
              ]"
              :title="layout.sidebarCollapsed ? item.label : undefined"
            >
              <svg
                class="h-5 w-5 shrink-0"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="1.5"
              >
                <path stroke-linecap="round" stroke-linejoin="round" :d="item.icon" />
              </svg>
              <span v-if="!layout.sidebarCollapsed" class="truncate">{{ item.label }}</span>
            </router-link>
          </template>
        </div>
      </div>
    </nav>

    <!-- Collapse Toggle -->
    <div class="border-t border-gray-200 p-2 dark:border-gray-700">
      <button
        class="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-gray-500 transition hover:bg-gray-100 hover:text-go4-secondary dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200"
        @click="layout.toggleSidebar"
      >
        <svg
          class="h-5 w-5 shrink-0 transition"
          :class="{ 'rotate-180': layout.sidebarCollapsed }"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M18.75 19.5l-7.5-7.5 7.5-7.5m-6 15L5.25 12l7.5-7.5"
          />
        </svg>
        <span v-if="!layout.sidebarCollapsed" class="truncate">Einklappen</span>
      </button>
    </div>
  </aside>
</template>
