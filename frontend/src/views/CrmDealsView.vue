<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useCrmStore } from '@/stores/crm'
import { useContactsStore } from '@/stores/contacts'
import PageHeader from '@/components/ui/PageHeader.vue'
import SearchInput from '@/components/ui/SearchInput.vue'
import ViewModeToggle from '@/components/ui/ViewModeToggle.vue'
import DataTable from '@/components/ui/DataTable.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import KanbanBoard from '@/components/crm/KanbanBoard.vue'
import PipelineSelector from '@/components/crm/PipelineSelector.vue'
import DealFormModal from '@/components/crm/DealFormModal.vue'

const router = useRouter()
const store = useCrmStore()
const contactsStore = useContactsStore()

// View state
const viewMode = ref('kanban')
const viewModes = [
  { value: 'kanban', icon: 'kanban', label: 'Kanban' },
  { value: 'table', icon: 'table', label: 'Tabelle' }
]

const searchQuery = ref('')
const selectedPipelineId = ref(null)

// Modal state
const showDealModal = ref(false)
const editingDeal = ref(null)
const defaultStageId = ref(null)
const modalLoading = ref(false)

// Table columns
const dealColumns = [
  { key: 'title', label: 'Titel', sortable: true },
  { key: 'company_name', label: 'Firma', sortable: true },
  { key: 'stage_name', label: 'Stage', sortable: true },
  { key: 'value', label: 'Wert', sortable: true },
  { key: 'expected_close', label: 'Abschluss', sortable: true },
  { key: 'priority', label: 'Priorität', sortable: true }
]

const currentPipeline = computed(() => {
  if (!selectedPipelineId.value) return null
  // Use currentPipeline from store if available (has full stages)
  if (
    store.currentPipeline?.id === selectedPipelineId.value &&
    store.currentPipeline?.stages?.length
  ) {
    return store.currentPipeline
  }
  // Fallback: build from pipelines list + kanbanBoard stages
  const pipeline = store.pipelines.find((p) => p.id === selectedPipelineId.value)
  if (!pipeline) return null
  return {
    ...pipeline,
    stages: store.kanbanBoard?.stages || []
  }
})

const totalValue = computed(() => {
  if (!store.kanbanBoard) return 0
  return store.kanbanBoard.stages.reduce(
    (sum, stage) => sum + parseFloat(stage.total_value || 0),
    0
  )
})

const formattedTotalValue = computed(() => {
  return new Intl.NumberFormat('de-DE', {
    style: 'currency',
    currency: 'EUR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(totalValue.value)
})

const dealCount = computed(() => {
  if (!store.kanbanBoard) return 0
  return store.kanbanBoard.stages.reduce((sum, stage) => sum + stage.deal_count, 0)
})

onMounted(async () => {
  await store.fetchPipelines()
  await contactsStore.fetchContacts()
  await contactsStore.fetchCompanies()

  if (store.defaultPipeline) {
    selectedPipelineId.value = store.defaultPipeline.id
    await loadBoard()
  }
})

watch(selectedPipelineId, async (newId) => {
  if (newId) {
    await loadBoard()
  }
})

async function loadBoard() {
  if (viewMode.value === 'kanban') {
    await store.fetchKanbanBoard(selectedPipelineId.value)
  } else {
    await store.fetchDeals({ pipeline_id: selectedPipelineId.value })
  }
}

async function openNewDealModal(stage = null) {
  editingDeal.value = null
  defaultStageId.value = stage?.id || null
  // Always fetch pipeline to ensure we have stages
  if (selectedPipelineId.value) {
    await store.fetchPipeline(selectedPipelineId.value)
  }
  showDealModal.value = true
}

async function openEditDealModal(deal) {
  editingDeal.value = deal
  defaultStageId.value = deal.stage_id
  // Ensure we have pipeline with stages
  if (selectedPipelineId.value) {
    await store.fetchPipeline(selectedPipelineId.value)
  }
  showDealModal.value = true
}

async function saveDeal(data) {
  modalLoading.value = true
  try {
    if (editingDeal.value) {
      await store.editDeal(editingDeal.value.id, data)
    } else {
      await store.addDeal(data)
    }
    showDealModal.value = false
    await loadBoard()
  } catch {
    // Error is set in store
  } finally {
    modalLoading.value = false
  }
}

async function moveDealToStage({ dealId, stageId }) {
  try {
    await store.moveDealToStage(dealId, stageId)
  } catch {
    // Error is set in store
  }
}

function goToDeal(deal) {
  router.push({ name: 'crm-deal-detail', params: { id: deal.id } })
}

function onSearch(query) {
  searchQuery.value = query
  // TODO: implement search filtering
}

function formatValue(value, currency = 'EUR') {
  if (!value) return '-'
  return new Intl.NumberFormat('de-DE', {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(value)
}

function formatDate(dateString) {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleDateString('de-DE')
}

const priorityLabels = {
  low: 'Niedrig',
  medium: 'Normal',
  high: 'Hoch'
}
</script>

<template>
  <div>
    <PageHeader
      title="Deals"
    >
      <template #actions>
        <button
          type="button"
          class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark"
          @click="openNewDealModal()"
        >
          + Deal
        </button>
      </template>
    </PageHeader>

    <!-- Controls -->
    <div class="mt-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div class="flex items-center gap-3">
        <PipelineSelector
          v-model="selectedPipelineId"
          :pipelines="store.pipelines"
        />
      </div>

      <div class="flex items-center gap-3">
        <SearchInput
          v-model="searchQuery"
          placeholder="Deals suchen..."
          class="w-64"
          @search="onSearch"
        />
        <ViewModeToggle
          v-model="viewMode"
          :modes="viewModes"
        />
      </div>
    </div>

    <!-- Main Content -->
    <div class="mt-6">
      <!-- Loading -->
      <div
        v-if="store.loading"
        class="flex items-center justify-center p-12"
      >
        <span class="text-go4-muted dark:text-gray-400">Laden...</span>
      </div>

      <!-- Error -->
      <div
        v-else-if="store.error"
        class="rounded-lg bg-red-50 dark:bg-red-900/20 p-4 text-red-700 dark:text-red-400"
      >
        {{ store.error }}
      </div>

      <!-- No Pipeline -->
      <EmptyState
        v-else-if="!selectedPipelineId"
        title="Keine Pipeline ausgewählt"
      />

      <!-- Kanban View -->
      <template v-else-if="viewMode === 'kanban' && store.kanbanBoard">
        <EmptyState
          v-if="store.kanbanBoard.stages.length === 0"
          title="Keine Stages"
        />

        <KanbanBoard
          v-else
          :stages="store.kanbanBoard.stages"
          @deal-click="goToDeal"
          @add-deal="openNewDealModal"
          @move-deal="moveDealToStage"
        />
      </template>

      <!-- Table View -->
      <template v-else-if="viewMode === 'table'">
        <EmptyState
          v-if="store.deals.length === 0"
          title="Keine Deals"
        >
          <template #action>
            <button
              type="button"
              class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark"
              @click="openNewDealModal()"
            >
              + Deal erstellen
            </button>
          </template>
        </EmptyState>

        <DataTable
          v-else
          :columns="dealColumns"
          :data="store.deals"
          @row-click="goToDeal"
        >
          <template #cell-title="{ row }">
            <span class="font-medium">{{ row.title }}</span>
          </template>
          <template #cell-value="{ row }">
            {{ formatValue(row.value, row.currency) }}
          </template>
          <template #cell-expected_close="{ value }">
            {{ formatDate(value) }}
          </template>
          <template #cell-priority="{ value }">
            <span
              class="rounded-full px-2 py-0.5 text-xs font-medium"
              :class="{
                'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300': value === 'low',
                'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300':
                  value === 'medium',
                'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300':
                  value === 'high'
              }"
            >
              {{ priorityLabels[value] }}
            </span>
          </template>
        </DataTable>
      </template>
    </div>

    <!-- Deal Form Modal -->
    <DealFormModal
      :open="showDealModal"
      :deal="editingDeal"
      :pipeline="currentPipeline"
      :default-stage-id="defaultStageId"
      :contacts="contactsStore.contacts"
      :companies="contactsStore.companies"
      :loading="modalLoading"
      @close="showDealModal = false"
      @save="saveDeal"
    />
  </div>
</template>
