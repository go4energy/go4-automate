<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useLayoutStore } from '@/stores/layout'

const route = useRoute()
const layout = useLayoutStore()

const navGroups = [
  {
    label: 'UEBERSICHT',
    items: [
      { to: '/', label: 'Dashboard', icon: 'dashboard' },
      { to: '/setup', label: 'Setup Wizard', icon: 'setup' }
    ]
  },
  {
    label: 'MARKETING',
    items: [
      { to: '/research', label: 'Research', icon: 'research' },
      { to: '/content', label: 'Content', icon: 'content' },
      { to: '/ads', label: 'Ads', icon: 'ads' }
    ]
  },
  {
    label: 'KONFIGURATION',
    items: [
      { to: '/prompts', label: 'Prompts', icon: 'prompts' },
      { href: 'https://n8n.go4.energy', label: 'n8n Workflows', icon: 'workflows' }
    ]
  }
]

const bottomItems = [{ to: '/leads', label: 'Leads', icon: 'leads' }]

function isActive(item) {
  if (item.to === '/') return route.path === '/'
  return route.path.startsWith(item.to)
}

const sidebarWidth = computed(() => (layout.sidebarCollapsed ? 'w-16' : 'w-64'))
</script>

<template>
  <aside
    :class="[
      sidebarWidth,
      'fixed inset-y-0 left-0 z-30 flex flex-col border-r border-gray-200 bg-white transition-all duration-200'
    ]"
  >
    <!-- Logo -->
    <div class="flex h-16 items-center border-b border-gray-200 px-4">
      <div class="flex items-center gap-2 overflow-hidden">
        <div
          class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-go4-primary text-sm font-bold text-white"
        >
          g4
        </div>
        <span
          v-if="!layout.sidebarCollapsed"
          class="whitespace-nowrap text-sm font-semibold text-go4-secondary"
        >
          go4-automate
        </span>
      </div>
    </div>

    <!-- Navigation -->
    <nav class="flex-1 overflow-y-auto px-2 py-4">
      <div v-for="group in navGroups" :key="group.label" class="mb-6">
        <p
          v-if="!layout.sidebarCollapsed"
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
                'text-gray-600 hover:bg-gray-100 hover:text-go4-secondary'
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
                <path
                  v-if="item.icon === 'workflows'"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M13.5 16.875h3.375m0 0h3.375m-3.375 0V13.5m0 3.375v3.375M6 10.5h2.25a2.25 2.25 0 002.25-2.25V6a2.25 2.25 0 00-2.25-2.25H6A2.25 2.25 0 003.75 6v2.25A2.25 2.25 0 006 10.5zm0 9.75h2.25A2.25 2.25 0 0010.5 18v-2.25a2.25 2.25 0 00-2.25-2.25H6a2.25 2.25 0 00-2.25 2.25V18A2.25 2.25 0 006 20.25zm9.75-9.75H18a2.25 2.25 0 002.25-2.25V6A2.25 2.25 0 0018 3.75h-2.25A2.25 2.25 0 0013.5 6v2.25a2.25 2.25 0 002.25 2.25z"
                />
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
                  : 'text-gray-600 hover:bg-gray-100 hover:text-go4-secondary'
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
                <!-- Dashboard -->
                <path
                  v-if="item.icon === 'dashboard'"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zm0 9.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zm0 9.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25a2.25 2.25 0 01-2.25-2.25v-2.25z"
                />
                <!-- Setup -->
                <path
                  v-if="item.icon === 'setup'"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 010 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 010-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28zM15 12a3 3 0 11-6 0 3 3 0 016 0z"
                />
                <!-- Content -->
                <path
                  v-if="item.icon === 'content'"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
                />
                <!-- Ads -->
                <path
                  v-if="item.icon === 'ads'"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M10.34 15.84c-.688-.06-1.386-.09-2.09-.09H7.5a4.5 4.5 0 110-9h.75c.704 0 1.402-.03 2.09-.09m0 9.18c.253.962.584 1.892.985 2.783.247.55.06 1.21-.463 1.511l-.657.38c-.551.318-1.26.117-1.527-.461a20.845 20.845 0 01-1.44-4.282m3.102.069a18.03 18.03 0 01-.59-4.59c0-1.586.205-3.124.59-4.59m0 9.18a23.848 23.848 0 018.835 2.535M10.34 6.66a23.847 23.847 0 008.835-2.535m0 0A23.74 23.74 0 0018.795 3m.38 1.125a23.91 23.91 0 011.014 5.395m-1.014 8.855c-.118.38-.245.754-.38 1.125m.38-1.125a23.91 23.91 0 001.014-5.395m0-3.46c.495.413.811 1.035.811 1.73 0 .695-.316 1.317-.811 1.73m0-3.46a24.347 24.347 0 010 3.46"
                />
                <!-- Research -->
                <path
                  v-if="item.icon === 'research'"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"
                />
                <!-- Prompts -->
                <path
                  v-if="item.icon === 'prompts'"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5"
                />
                <!-- Leads -->
                <path
                  v-if="item.icon === 'leads'"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z"
                />
              </svg>
              <span v-if="!layout.sidebarCollapsed" class="truncate">{{ item.label }}</span>
            </router-link>
          </template>
        </div>
      </div>

      <!-- Bottom nav items -->
      <div class="space-y-1">
        <router-link
          v-for="item in bottomItems"
          :key="item.label"
          :to="item.to"
          :class="[
            'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition',
            isActive(item)
              ? 'bg-go4-primary/10 text-go4-primary'
              : 'text-gray-600 hover:bg-gray-100 hover:text-go4-secondary'
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
            <path
              v-if="item.icon === 'leads'"
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z"
            />
          </svg>
          <span v-if="!layout.sidebarCollapsed" class="truncate">{{ item.label }}</span>
        </router-link>
      </div>
    </nav>

    <!-- Collapse Toggle -->
    <div class="border-t border-gray-200 p-2">
      <button
        class="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-gray-500 transition hover:bg-gray-100 hover:text-go4-secondary"
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
