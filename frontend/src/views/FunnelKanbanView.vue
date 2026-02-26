<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useFunnelsStore } from '@/stores/funnels'
import PageHeader from '@/components/ui/PageHeader.vue'
import ProspectCard from '@/components/funnels/ProspectCard.vue'

const route = useRoute()
const router = useRouter()
const store = useFunnelsStore()

const funnelId = computed(() => Number(route.params.id))
const draggingProspect = ref(null)
const dragOverStage = ref(null)

const funnel = computed(() => store.currentFunnel)
const kanbanData = computed(() => store.kanbanData)

onMounted(async () => {
  await loadKanban()
})

watch(funnelId, async () => {
  await loadKanban()
})

async function loadKanban() {
  await store.fetchFunnel(funnelId.value)
  await store.fetchKanban(funnelId.value)
}

function goBack() {
  router.push(`/funnels/${funnelId.value}`)
}

function openProspect(prospect) {
  router.push(`/funnels/prospects/${prospect.id}`)
}

function onDragStart(event, prospect) {
  draggingProspect.value = prospect
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('text/plain', prospect.id)
}

function onDragEnd() {
  draggingProspect.value = null
  dragOverStage.value = null
}

function onDragOver(event, stageId) {
  event.preventDefault()
  dragOverStage.value = stageId
}

function onDragLeave() {
  dragOverStage.value = null
}

async function onDrop(event, stageId) {
  event.preventDefault()
  dragOverStage.value = null

  if (!draggingProspect.value) return
  if (draggingProspect.value.stage_id === stageId) return

  try {
    await store.moveProspect(draggingProspect.value.id, stageId)
    await store.fetchKanban(funnelId.value)
  } catch {
    // Error is in store
  }

  draggingProspect.value = null
}

function getProspectCount(stage) {
  return stage.prospects?.length || 0
}

function getStageTotal(stage) {
  const prospects = stage.prospects || []
  return prospects.reduce((sum, p) => sum + (p.score || 0), 0)
}
</script>

<template>
  <div class="flex h-screen flex-col bg-go4-bg dark:bg-gray-900">
    <!-- Header -->
    <PageHeader
      :title="funnel?.name || 'Kanban'"
      subtitle="Drag & Drop zum Verschieben"
    >
      <template #actions>
        <button
          class="flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700"
          @click="goBack"
        >
          <svg
            class="h-5 w-5"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fill-rule="evenodd"
              d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z"
              clip-rule="evenodd"
            />
          </svg>
          Zurueck
        </button>
        <button
          class="flex items-center gap-2 rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark"
          @click="loadKanban"
        >
          <svg
            class="h-5 w-5"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fill-rule="evenodd"
              d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z"
              clip-rule="evenodd"
            />
          </svg>
          Aktualisieren
        </button>
      </template>
    </PageHeader>

    <!-- Loading -->
    <div
      v-if="store.loading"
      class="flex flex-1 items-center justify-center"
    >
      <span class="text-go4-muted dark:text-gray-400">Laden...</span>
    </div>

    <!-- Error -->
    <div
      v-else-if="store.error"
      class="flex flex-1 items-center justify-center px-4"
    >
      <div class="rounded-lg bg-red-50 p-4 text-red-700 dark:bg-red-900/30 dark:text-red-300">
        {{ store.error }}
      </div>
    </div>

    <!-- Kanban Board -->
    <div
      v-else
      class="flex flex-1 gap-4 overflow-x-auto px-4 py-6 sm:px-6 lg:px-8"
    >
      <div
        v-for="stage in kanbanData"
        :key="stage.stage_id"
        class="flex w-80 flex-shrink-0 flex-col rounded-lg bg-gray-100 dark:bg-gray-800"
        :class="{
          'ring-2 ring-go4-primary': dragOverStage === stage.stage_id
        }"
        @dragover="onDragOver($event, stage.stage_id)"
        @dragleave="onDragLeave"
        @drop="onDrop($event, stage.stage_id)"
      >
        <!-- Stage Header -->
        <div class="flex items-center gap-3 border-b border-gray-200 dark:border-gray-700 p-4">
          <div
            class="h-3 w-3 rounded-full flex-shrink-0"
            :style="{ backgroundColor: stage.stage_color }"
          />
          <div class="flex-1 min-w-0">
            <h3 class="font-semibold text-go4-secondary dark:text-white truncate">
              {{ stage.stage_name }}
            </h3>
          </div>
          <div class="flex items-center gap-2">
            <span
              class="rounded-full bg-gray-200 dark:bg-gray-700 px-2 py-0.5 text-xs font-medium text-gray-700 dark:text-gray-300"
            >
              {{ getProspectCount(stage) }}
            </span>
          </div>
        </div>

        <!-- Stage Flags -->
        <div
          v-if="stage.is_handoff || stage.is_disqualified"
          class="flex gap-2 px-4 py-2"
        >
          <span
            v-if="stage.is_handoff"
            class="rounded-full bg-green-100 dark:bg-green-900 px-2 py-0.5 text-xs font-medium text-green-700 dark:text-green-300"
          >
            Handoff Stage
          </span>
          <span
            v-if="stage.is_disqualified"
            class="rounded-full bg-red-100 dark:bg-red-900 px-2 py-0.5 text-xs font-medium text-red-700 dark:text-red-300"
          >
            Disqualifiziert
          </span>
        </div>

        <!-- Prospects List -->
        <div class="flex-1 overflow-y-auto p-3 space-y-3">
          <div
            v-if="!stage.prospects?.length"
            class="py-8 text-center text-sm text-go4-muted dark:text-gray-500"
          >
            Keine Prospects
          </div>

          <div
            v-for="prospect in stage.prospects"
            :key="prospect.id"
            draggable="true"
            class="cursor-move transition-transform"
            :class="{
              'opacity-50 scale-95': draggingProspect?.id === prospect.id
            }"
            @dragstart="onDragStart($event, prospect)"
            @dragend="onDragEnd"
          >
            <ProspectCard
              :prospect="prospect"
              compact
              @click="openProspect"
            />
          </div>
        </div>

        <!-- Stage Footer -->
        <div
          class="border-t border-gray-200 dark:border-gray-700 px-4 py-3 text-xs text-go4-muted dark:text-gray-400"
        >
          <div class="flex justify-between">
            <span>Avg. Score:</span>
            <span class="font-medium">
              {{
                getProspectCount(stage) > 0
                  ? Math.round(getStageTotal(stage) / getProspectCount(stage))
                  : 0
              }}
            </span>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div
        v-if="kanbanData.length === 0"
        class="flex flex-1 items-center justify-center"
      >
        <div class="text-center">
          <svg
            class="mx-auto h-12 w-12 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2"
            />
          </svg>
          <h3 class="mt-2 text-sm font-medium text-go4-secondary dark:text-white">
            Keine Stages
          </h3>
          <p class="mt-1 text-sm text-go4-muted dark:text-gray-400">
            Erstelle zuerst Stages in den Funnel-Einstellungen.
          </p>
          <button
            class="mt-4 rounded-lg bg-go4-primary px-4 py-2 text-sm text-white hover:bg-go4-primary-dark"
            @click="router.push(`/funnels/${funnelId}`)"
          >
            Zu Einstellungen
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
