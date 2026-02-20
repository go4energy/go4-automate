<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useLayoutStore } from '@/stores/layout'

const route = useRoute()
const layout = useLayoutStore()

const routeTitles = {
  dashboard: 'Dashboard',
  collector: 'Collector',
  'collector-source-new': 'Neue Quelle',
  'collector-source-edit': 'Quelle bearbeiten',
  'collector-topic-new': 'Eigenes Thema',
  creator: 'Creator',
  'creator-edit': 'Content bearbeiten',
  distributor: 'Distributor',
  'distributor-campaign-config': 'Kampagne konfigurieren',
  crm: 'CRM',
  prompts: 'Prompt Registry',
  'prompt-new': 'Neuer Prompt',
  'prompt-edit': 'Prompt bearbeiten',
  setup: 'Setup Wizard'
}

const breadcrumbs = computed(() => {
  const crumbs = [{ label: 'Dashboard', to: '/' }]
  const name = route.name

  if (name === 'dashboard') return crumbs

  const parentMap = {
    'collector-source-new': { label: 'Collector', to: '/collector' },
    'collector-source-edit': { label: 'Collector', to: '/collector' },
    'collector-topic-new': { label: 'Collector', to: '/collector' },
    'creator-edit': { label: 'Creator', to: '/creator' },
    'distributor-campaign-config': { label: 'Distributor', to: '/distributor' },
    'prompt-new': { label: 'Prompts', to: '/prompts' },
    'prompt-edit': { label: 'Prompts', to: '/prompts' }
  }

  if (parentMap[name]) {
    crumbs.push(parentMap[name])
  }

  crumbs.push({ label: routeTitles[name] || name, to: null })
  return crumbs
})
</script>

<template>
  <header
    class="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-gray-200 bg-white px-6"
  >
    <!-- Breadcrumbs -->
    <nav class="flex items-center gap-1 text-sm">
      <template v-for="(crumb, i) in breadcrumbs" :key="i">
        <span v-if="i > 0" class="text-gray-300">/</span>
        <router-link
          v-if="crumb.to && i < breadcrumbs.length - 1"
          :to="crumb.to"
          class="text-gray-500 hover:text-go4-secondary"
        >
          {{ crumb.label }}
        </router-link>
        <span v-else class="font-medium text-go4-secondary">
          {{ crumb.label }}
        </span>
      </template>
    </nav>

    <!-- Right: Chat toggle -->
    <button
      class="relative rounded-lg p-2 text-gray-500 transition hover:bg-gray-100 hover:text-go4-secondary"
      title="Chat"
      @click="layout.toggleChat"
    >
      <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z"
        />
      </svg>
    </button>
  </header>
</template>
