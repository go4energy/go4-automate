<script setup>
import { onMounted } from 'vue'
import { useLeadStore } from '@/stores/leads'
import { useContentStore } from '@/stores/content'
import { useAdStore } from '@/stores/ads'
import { useResearchStore } from '@/stores/research'
import { useActivityStore } from '@/stores/activity'
import PageHeader from '@/components/ui/PageHeader.vue'
import StatCard from '@/components/ui/StatCard.vue'
import ActivityFeed from '@/components/ui/ActivityFeed.vue'

const leadStore = useLeadStore()
const contentStore = useContentStore()
const adStore = useAdStore()
const researchStore = useResearchStore()
const activityStore = useActivityStore()

onMounted(() => {
  leadStore.fetchLeads()
  contentStore.fetchPieces()
  adStore.fetchDashboard()
  researchStore.fetchTopics()
  researchStore.fetchSources()
  activityStore.fetchActivities(null, 15)
  activityStore.fetchStats(7)
})
</script>

<template>
  <div>
    <PageHeader title="Dashboard" subtitle="Marketing Automation Platform" />

    <!-- Stats Row -->
    <div class="mt-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
      <StatCard
        label="Leads"
        :value="leadStore.totalLeads"
        :trend="leadStore.activeLeads > 0 ? `${leadStore.activeLeads} aktiv` : null"
        color="text-go4-secondary"
      />
      <StatCard
        label="Content"
        :value="contentStore.pieces.length"
        :trend="
          contentStore.stats.published > 0
            ? `${contentStore.stats.published} ver\u00f6ffentlicht`
            : null
        "
        color="text-go4-secondary"
      />
      <StatCard
        label="Ad Spend heute"
        :value="`${adStore.totalSpendToday} EUR`"
        :trend="adStore.totalLeadsToday > 0 ? `${adStore.totalLeadsToday} Leads heute` : null"
        color="text-go4-secondary"
      />
      <StatCard
        label="Research Topics"
        :value="researchStore.suggestedTopics.length"
        :trend="`${researchStore.activeSources.length} Quellen aktiv`"
        color="text-go4-secondary"
      />
    </div>

    <!-- Main Content: Module Cards + Activity Feed -->
    <div class="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-3">
      <!-- Module Summary Cards (left 2/3) -->
      <div class="space-y-4 lg:col-span-2">
        <!-- Content Pipeline -->
        <router-link
          to="/content"
          class="block rounded-lg bg-white p-5 shadow-sm transition hover:shadow-md"
        >
          <div class="flex items-center justify-between">
            <div>
              <h3 class="text-sm font-semibold text-gray-800">Content Pipeline</h3>
              <p class="mt-1 text-xs text-gray-500">
                {{ contentStore.stats.draft }} Entwuerfe &middot;
                {{ contentStore.stats.scheduled }} geplant &middot;
                {{ contentStore.stats.published }} veroeffentlicht
              </p>
            </div>
            <div class="flex gap-2">
              <span
                v-if="contentStore.stats.draft > 0"
                class="rounded-full bg-yellow-100 px-2 py-0.5 text-xs font-medium text-yellow-700"
              >
                {{ contentStore.stats.draft }} Drafts
              </span>
              <span
                v-if="contentStore.stats.failed > 0"
                class="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700"
              >
                {{ contentStore.stats.failed }} fehlgeschlagen
              </span>
            </div>
          </div>
        </router-link>

        <!-- Ad Management -->
        <router-link
          to="/ads"
          class="block rounded-lg bg-white p-5 shadow-sm transition hover:shadow-md"
        >
          <div class="flex items-center justify-between">
            <div>
              <h3 class="text-sm font-semibold text-gray-800">Ad Management</h3>
              <p class="mt-1 text-xs text-gray-500">
                {{ adStore.activeCampaigns }} aktive Kampagnen &middot;
                {{ adStore.totalSpendToday }} EUR Spend heute
              </p>
            </div>
            <span
              v-if="adStore.activeCampaigns > 0"
              class="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700"
            >
              {{ adStore.activeCampaigns }} aktiv
            </span>
          </div>
        </router-link>

        <!-- Research -->
        <router-link
          to="/research"
          class="block rounded-lg bg-white p-5 shadow-sm transition hover:shadow-md"
        >
          <div class="flex items-center justify-between">
            <div>
              <h3 class="text-sm font-semibold text-gray-800">Research Agent</h3>
              <p class="mt-1 text-xs text-gray-500">
                {{ researchStore.activeSources.length }} aktive Quellen &middot;
                {{ researchStore.suggestedTopics.length }} Topic-Vorschlaege
              </p>
            </div>
            <span
              v-if="researchStore.newFindings.length > 0"
              class="rounded-full bg-purple-100 px-2 py-0.5 text-xs font-medium text-purple-700"
            >
              {{ researchStore.newFindings.length }} neue Findings
            </span>
          </div>
        </router-link>

        <!-- Quick Links Row -->
        <div class="grid grid-cols-2 gap-4">
          <router-link
            to="/leads"
            class="rounded-lg bg-white p-4 shadow-sm transition hover:shadow-md"
          >
            <h3 class="text-sm font-semibold text-gray-800">Leads</h3>
            <p class="mt-1 text-xs text-gray-500">{{ leadStore.activeLeads }} aktive Leads</p>
          </router-link>
          <router-link
            to="/prompts"
            class="rounded-lg bg-white p-4 shadow-sm transition hover:shadow-md"
          >
            <h3 class="text-sm font-semibold text-gray-800">Prompt Registry</h3>
            <p class="mt-1 text-xs text-gray-500">Prompts verwalten</p>
          </router-link>
        </div>
      </div>

      <!-- Activity Feed (right 1/3) -->
      <div class="rounded-lg bg-white p-4 shadow-sm">
        <div class="mb-3 flex items-center justify-between">
          <h3 class="text-sm font-semibold text-gray-800">Letzte Aktivitaeten</h3>
        </div>
        <div v-if="activityStore.loading" class="py-6 text-center text-sm text-gray-400">
          Laden...
        </div>
        <ActivityFeed
          v-else
          :activities="activityStore.activities"
          :compact="true"
          :max-items="10"
        />
      </div>
    </div>
  </div>
</template>
