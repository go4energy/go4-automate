<script setup>
import { onMounted } from 'vue'
import { useLeadStore } from '@/stores/leads'
import { useContentStore } from '@/stores/content'
import { useAdStore } from '@/stores/ads'
import { usePromptStore } from '@/stores/prompts'
import { useResearchStore } from '@/stores/research'

const leadStore = useLeadStore()
const contentStore = useContentStore()
const adStore = useAdStore()
const promptStore = usePromptStore()
const researchStore = useResearchStore()

onMounted(() => {
  leadStore.fetchLeads()
  contentStore.fetchPieces()
  adStore.fetchDashboard()
  promptStore.fetchPrompts()
  researchStore.fetchTopics()
  researchStore.fetchSources()
})
</script>

<template>
  <div class="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
    <h1 class="text-3xl font-bold text-go4-secondary">go4-automate Dashboard</h1>
    <p class="mt-2 text-go4-muted">Marketing Automation Platform</p>

    <div v-if="leadStore.loading" class="mt-8 flex items-center justify-center">
      <span class="text-go4-muted">Laden...</span>
    </div>

    <div v-else-if="leadStore.error" class="mt-8 rounded-lg bg-red-50 p-4 text-red-700">
      {{ leadStore.error }}
    </div>

    <div v-else class="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
      <router-link to="/leads" class="rounded-lg bg-white p-6 shadow-sm transition hover:shadow-md">
        <h2 class="text-sm font-medium text-go4-muted">Leads</h2>
        <p class="mt-2 text-3xl font-semibold text-go4-secondary">
          {{ leadStore.totalLeads }}
        </p>
      </router-link>
      <router-link
        to="/content"
        class="rounded-lg bg-white p-6 shadow-sm transition hover:shadow-md"
      >
        <h2 class="text-sm font-medium text-go4-muted">Content</h2>
        <p class="mt-2 text-3xl font-semibold text-go4-secondary">
          {{ contentStore.pieces.length }}
        </p>
        <p v-if="contentStore.stats.published > 0" class="mt-1 text-xs text-go4-muted">
          {{ contentStore.stats.published }} veröffentlicht
        </p>
      </router-link>
      <router-link to="/ads" class="rounded-lg bg-white p-6 shadow-sm transition hover:shadow-md">
        <h2 class="text-sm font-medium text-go4-muted">Ad Management</h2>
        <p class="mt-2 text-3xl font-semibold text-go4-secondary">
          {{ adStore.totalSpendToday }} EUR
        </p>
        <p v-if="adStore.totalLeadsToday > 0" class="mt-1 text-xs text-go4-muted">
          {{ adStore.totalLeadsToday }} Leads heute
        </p>
      </router-link>
      <router-link
        to="/research"
        class="rounded-lg bg-white p-6 shadow-sm transition hover:shadow-md"
      >
        <h2 class="text-sm font-medium text-go4-muted">Research Agent</h2>
        <p class="mt-2 text-3xl font-semibold text-go4-secondary">
          {{ researchStore.suggestedTopics.length }}
        </p>
        <p class="mt-1 text-xs text-go4-muted">
          {{ researchStore.activeSources.length }} Quellen aktiv
        </p>
      </router-link>
      <router-link
        to="/prompts"
        class="rounded-lg bg-white p-6 shadow-sm transition hover:shadow-md"
      >
        <h2 class="text-sm font-medium text-go4-muted">Prompt Registry</h2>
        <p class="mt-2 text-3xl font-semibold text-go4-secondary">
          {{ promptStore.prompts.length }}
        </p>
        <p class="mt-1 text-xs text-go4-muted">KI-Prompts verwalten</p>
      </router-link>
      <a
        href="https://n8n.go4.energy"
        target="_blank"
        class="rounded-lg bg-white p-6 shadow-sm transition hover:shadow-md"
      >
        <h2 class="text-sm font-medium text-go4-muted">Workflows</h2>
        <p class="mt-2 text-3xl font-semibold text-go4-secondary">n8n</p>
        <p class="mt-1 text-xs text-go4-muted">Automatisierung konfigurieren</p>
      </a>
    </div>
  </div>
</template>
