<script setup>
import { onMounted } from 'vue'
import { useCrmStore } from '@/stores/crm'
import { useCreatorStore } from '@/stores/creator'
import { useDistributorStore } from '@/stores/distributor'
import { useCollectorStore } from '@/stores/collector'
import { useActivityStore } from '@/stores/activity'
import { useBroadcasterStore } from '@/stores/broadcaster'
import PageHeader from '@/components/ui/PageHeader.vue'
import StatCard from '@/components/ui/StatCard.vue'
import ActivityFeed from '@/components/ui/ActivityFeed.vue'

const crmStore = useCrmStore()
const creatorStore = useCreatorStore()
const distributorStore = useDistributorStore()
const collectorStore = useCollectorStore()
const activityStore = useActivityStore()
const broadcasterStore = useBroadcasterStore()

onMounted(() => {
  crmStore.fetchContacts()
  creatorStore.fetchPieces()
  distributorStore.fetchDashboard()
  collectorStore.fetchTopics()
  collectorStore.fetchSources()
  activityStore.fetchActivities(null, 15)
  activityStore.fetchStats(7)
  broadcasterStore.fetchChannels()
})
</script>

<template>
  <div>
    <PageHeader title="Dashboard" subtitle="Marketing Automation Platform" />

    <!-- Stats Row -->
    <div class="mt-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
      <StatCard
        label="Kontakte"
        :value="crmStore.totalContacts"
        :trend="
          crmStore.activeContacts.length > 0 ? `${crmStore.activeContacts.length} aktiv` : null
        "
      />
      <StatCard
        label="Content"
        :value="creatorStore.pieces.length"
        :trend="
          creatorStore.stats.published > 0
            ? `${creatorStore.stats.published} ver\u00f6ffentlicht`
            : null
        "
      />
      <StatCard
        label="Ad Spend heute"
        :value="`${distributorStore.totalSpendToday} EUR`"
        :trend="
          distributorStore.totalLeadsToday > 0
            ? `${distributorStore.totalLeadsToday} Leads heute`
            : null
        "
      />
      <StatCard
        label="Collector Topics"
        :value="collectorStore.suggestedTopics.length"
        :trend="`${collectorStore.activeSources.length} Quellen aktiv`"
      />
    </div>

    <!-- Main Content: Module Cards + Activity Feed -->
    <div class="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-3">
      <!-- Module Summary Cards (left 2/3) -->
      <div class="space-y-4 lg:col-span-2">
        <!-- Creator Pipeline -->
        <router-link
          to="/creator"
          class="block rounded-lg bg-white p-5 shadow-sm transition hover:shadow-md dark:bg-gray-800 dark:hover:bg-gray-750"
        >
          <div class="flex items-center justify-between">
            <div>
              <h3 class="text-sm font-semibold text-gray-800 dark:text-gray-200">
                Creator Pipeline
              </h3>
              <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
                {{ creatorStore.stats.draft }} Entwuerfe &middot;
                {{ creatorStore.stats.scheduled }} geplant &middot;
                {{ creatorStore.stats.published }} veroeffentlicht
              </p>
            </div>
            <div class="flex gap-2">
              <span
                v-if="creatorStore.stats.draft > 0"
                class="rounded-full bg-yellow-100 px-2 py-0.5 text-xs font-medium text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400"
              >
                {{ creatorStore.stats.draft }} Drafts
              </span>
              <span
                v-if="creatorStore.stats.failed > 0"
                class="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700 dark:bg-red-900/30 dark:text-red-400"
              >
                {{ creatorStore.stats.failed }} fehlgeschlagen
              </span>
            </div>
          </div>
        </router-link>

        <!-- Distributor -->
        <router-link
          to="/distributor"
          class="block rounded-lg bg-white p-5 shadow-sm transition hover:shadow-md dark:bg-gray-800 dark:hover:bg-gray-750"
        >
          <div class="flex items-center justify-between">
            <div>
              <h3 class="text-sm font-semibold text-gray-800 dark:text-gray-200">Distributor</h3>
              <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
                {{ distributorStore.activeCampaigns.length }} aktive Kampagnen &middot;
                {{ distributorStore.totalSpendToday }} EUR Spend heute
              </p>
            </div>
            <span
              v-if="distributorStore.activeCampaigns.length > 0"
              class="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700 dark:bg-green-900/30 dark:text-green-400"
            >
              {{ distributorStore.activeCampaigns.length }} aktiv
            </span>
          </div>
        </router-link>

        <!-- Collector -->
        <router-link
          to="/collector"
          class="block rounded-lg bg-white p-5 shadow-sm transition hover:shadow-md dark:bg-gray-800 dark:hover:bg-gray-750"
        >
          <div class="flex items-center justify-between">
            <div>
              <h3 class="text-sm font-semibold text-gray-800 dark:text-gray-200">Collector</h3>
              <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
                {{ collectorStore.activeSources.length }} aktive Quellen &middot;
                {{ collectorStore.suggestedTopics.length }} Topic-Vorschlaege
              </p>
            </div>
            <span
              v-if="collectorStore.newFindings.length > 0"
              class="rounded-full bg-purple-100 px-2 py-0.5 text-xs font-medium text-purple-700 dark:bg-purple-900/30 dark:text-purple-400"
            >
              {{ collectorStore.newFindings.length }} neue Findings
            </span>
          </div>
        </router-link>

        <!-- Broadcaster -->
        <router-link
          to="/broadcaster"
          class="block rounded-lg bg-white p-5 shadow-sm transition hover:shadow-md dark:bg-gray-800 dark:hover:bg-gray-750"
        >
          <div class="flex items-center justify-between">
            <div>
              <h3 class="text-sm font-semibold text-gray-800 dark:text-gray-200">Broadcaster</h3>
              <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
                {{ broadcasterStore.activeChannels.length }} aktive Channels &middot;
                {{ broadcasterStore.totalEpisodes }} Episoden
              </p>
            </div>
            <span
              v-if="broadcasterStore.totalListeners > 0"
              class="rounded-full bg-sky-100 px-2 py-0.5 text-xs font-medium text-sky-700 dark:bg-sky-900/30 dark:text-sky-400"
            >
              {{ broadcasterStore.totalListeners }} Listener
            </span>
          </div>
        </router-link>

        <!-- Quick Links Row -->
        <div class="grid grid-cols-2 gap-4">
          <router-link
            to="/crm"
            class="rounded-lg bg-white p-4 shadow-sm transition hover:shadow-md dark:bg-gray-800 dark:hover:bg-gray-750"
          >
            <h3 class="text-sm font-semibold text-gray-800 dark:text-gray-200">CRM</h3>
            <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
              {{ crmStore.activeContacts.length }} aktive Kontakte
            </p>
          </router-link>
          <router-link
            to="/settings/prompts"
            class="rounded-lg bg-white p-4 shadow-sm transition hover:shadow-md dark:bg-gray-800 dark:hover:bg-gray-750"
          >
            <h3 class="text-sm font-semibold text-gray-800 dark:text-gray-200">Prompt Registry</h3>
            <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">Prompts verwalten</p>
          </router-link>
        </div>
      </div>

      <!-- Activity Feed (right 1/3) -->
      <div class="rounded-lg bg-white p-4 shadow-sm dark:bg-gray-800">
        <div class="mb-3 flex items-center justify-between">
          <h3 class="text-sm font-semibold text-gray-800 dark:text-gray-200">
            Letzte Aktivitaeten
          </h3>
        </div>
        <div
          v-if="activityStore.loading"
          class="py-6 text-center text-sm text-gray-400 dark:text-gray-500"
        >
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
