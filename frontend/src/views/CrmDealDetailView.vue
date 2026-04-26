<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCrmStore } from '@/stores/crm'
import { useContactsStore } from '@/stores/contacts'
import { getDealActivities, createActivity } from '@/api/crm'
import PageHeader from '@/components/ui/PageHeader.vue'
import DealFormModal from '@/components/crm/DealFormModal.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import ActivityTimeline from '@/components/crm/ActivityTimeline.vue'
import TaskList from '@/components/crm/TaskList.vue'

const route = useRoute()
const router = useRouter()
const store = useCrmStore()
const contactsStore = useContactsStore()

const dealId = computed(() => parseInt(route.params.id))

// View state
const activeTab = ref('overview')
const tabs = [
  { id: 'overview', label: 'Übersicht' },
  { id: 'activities', label: 'Aktivitäten' },
  { id: 'tasks', label: 'Aufgaben' }
]

// Modal state
const showEditModal = ref(false)
const showDeleteDialog = ref(false)
const modalLoading = ref(false)

// Activities
const activities = ref([])
const activitiesLoading = ref(false)

// Tasks
const dealTasks = computed(() => store.tasks.filter((t) => t.deal_id === dealId.value))

const deal = computed(() => store.currentDeal)

const pipeline = computed(() => {
  if (!deal.value) return null
  return store.pipelines.find((p) => p.id === deal.value.pipeline_id)
})

const stage = computed(() => {
  if (!pipeline.value || !deal.value) return null
  return pipeline.value.stages?.find((s) => s.id === deal.value.stage_id)
})

const contact = computed(() => {
  if (!deal.value?.contact_id) return null
  return contactsStore.contacts.find((c) => c.id === deal.value.contact_id)
})

const company = computed(() => {
  if (!deal.value?.company_id) return null
  return contactsStore.companies.find((c) => c.id === deal.value.company_id)
})

const formattedValue = computed(() => {
  if (!deal.value?.value) return '-'
  return new Intl.NumberFormat('de-DE', {
    style: 'currency',
    currency: deal.value.currency || 'EUR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(deal.value.value)
})

const formattedExpectedClose = computed(() => {
  if (!deal.value?.expected_close) return '-'
  return new Date(deal.value.expected_close).toLocaleDateString('de-DE')
})

const priorityConfig = {
  low: { label: 'Niedrig', class: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300' },
  medium: {
    label: 'Normal',
    class: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
  },
  high: {
    label: 'Hoch',
    class: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300'
  }
}

const statusConfig = {
  open: {
    label: 'Offen',
    class: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
  },
  won: {
    label: 'Gewonnen',
    class: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
  },
  lost: { label: 'Verloren', class: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300' }
}

onMounted(async () => {
  await Promise.all([
    store.fetchPipelines(),
    store.fetchDeal(dealId.value),
    store.fetchTasks({ deal_id: dealId.value }),
    contactsStore.fetchContacts(),
    contactsStore.fetchCompanies()
  ])
  await loadActivities()
})

async function loadActivities() {
  activitiesLoading.value = true
  try {
    const { data } = await getDealActivities(dealId.value)
    activities.value = data
  } catch {
    // Error handled silently
  } finally {
    activitiesLoading.value = false
  }
}

function goBack() {
  router.push({ name: 'crm-deals' })
}

function openEditModal() {
  showEditModal.value = true
}

async function saveDeal(data) {
  modalLoading.value = true
  try {
    await store.editDeal(dealId.value, data)
    showEditModal.value = false
  } catch {
    // Error is set in store
  } finally {
    modalLoading.value = false
  }
}

function confirmDelete() {
  showDeleteDialog.value = true
}

async function deleteDeal() {
  try {
    await store.removeDeal(dealId.value)
    router.push({ name: 'crm-deals' })
  } catch {
    // Error is set in store
  }
}

async function addActivity(activityData) {
  try {
    await createActivity({
      ...activityData,
      deal_id: dealId.value
    })
    await loadActivities()
  } catch {
    // Error handled silently
  }
}

async function markWon() {
  try {
    await store.editDeal(dealId.value, { status: 'won' })
  } catch {
    // Error is set in store
  }
}

async function markLost() {
  try {
    await store.editDeal(dealId.value, { status: 'lost' })
  } catch {
    // Error is set in store
  }
}
</script>

<template>
  <div>
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

    <!-- Content -->
    <template v-else-if="deal">
      <!-- Header -->
      <div class="mb-6">
        <button
          type="button"
          class="mb-4 flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          @click="goBack"
        >
          <svg
            class="h-4 w-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M15 19l-7-7 7-7"
            />
          </svg>
          Zurück zu Deals
        </button>

        <div class="flex items-start justify-between">
          <div>
            <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">
              {{ deal.title }}
            </h1>
            <div class="mt-1 flex items-center gap-3 text-sm text-gray-500 dark:text-gray-400">
              <span v-if="company">{{ company.name }}</span>
              <span
                v-if="stage"
                class="flex items-center gap-1"
              >
                <span
                  class="h-2 w-2 rounded-full"
                  :style="{ backgroundColor: stage.color }"
                />
                {{ stage.name }}
              </span>
              <span
                class="rounded-full px-2 py-0.5 text-xs font-medium"
                :class="statusConfig[deal.status]?.class"
              >
                {{ statusConfig[deal.status]?.label }}
              </span>
            </div>
          </div>

          <div class="flex items-center gap-2">
            <template v-if="deal.status === 'open'">
              <button
                type="button"
                class="rounded-lg bg-green-600 px-3 py-2 text-sm font-medium text-white hover:bg-green-700"
                @click="markWon"
              >
                Gewonnen
              </button>
              <button
                type="button"
                class="rounded-lg bg-red-600 px-3 py-2 text-sm font-medium text-white hover:bg-red-700"
                @click="markLost"
              >
                Verloren
              </button>
            </template>
            <button
              type="button"
              class="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600"
              @click="openEditModal"
            >
              Bearbeiten
            </button>
            <button
              type="button"
              class="rounded-lg border border-red-300 dark:border-red-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20"
              @click="confirmDelete"
            >
              Löschen
            </button>
          </div>
        </div>
      </div>

      <!-- Tabs -->
      <div class="border-b border-gray-200 dark:border-gray-700 mb-6">
        <nav class="-mb-px flex gap-6">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            type="button"
            class="border-b-2 pb-3 text-sm font-medium transition-colors"
            :class="
              activeTab === tab.id
                ? 'border-go4-primary text-go4-primary'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
            "
            @click="activeTab = tab.id"
          >
            {{ tab.label }}
          </button>
        </nav>
      </div>

      <!-- Tab Content -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Main Content -->
        <div class="lg:col-span-2">
          <!-- Overview Tab -->
          <template v-if="activeTab === 'overview'">
            <div
              class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6"
            >
              <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                Details
              </h2>

              <dl class="space-y-4">
                <div class="flex justify-between">
                  <dt class="text-sm text-gray-500 dark:text-gray-400">
                    Wert
                  </dt>
                  <dd class="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {{ formattedValue }}
                  </dd>
                </div>
                <div class="flex justify-between">
                  <dt class="text-sm text-gray-500 dark:text-gray-400">
                    Priorität
                  </dt>
                  <dd>
                    <span
                      class="rounded-full px-2 py-0.5 text-xs font-medium"
                      :class="priorityConfig[deal.priority]?.class"
                    >
                      {{ priorityConfig[deal.priority]?.label }}
                    </span>
                  </dd>
                </div>
                <div class="flex justify-between">
                  <dt class="text-sm text-gray-500 dark:text-gray-400">
                    Abschluss erwartet
                  </dt>
                  <dd class="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {{ formattedExpectedClose }}
                  </dd>
                </div>
                <div class="flex justify-between">
                  <dt class="text-sm text-gray-500 dark:text-gray-400">
                    Pipeline
                  </dt>
                  <dd class="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {{ pipeline?.name || '-' }}
                  </dd>
                </div>
                <div class="flex justify-between">
                  <dt class="text-sm text-gray-500 dark:text-gray-400">
                    Stage
                  </dt>
                  <dd class="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {{ stage?.name || '-' }}
                  </dd>
                </div>
              </dl>

              <div
                v-if="deal.description"
                class="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700"
              >
                <h3 class="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                  Beschreibung
                </h3>
                <p class="text-sm text-gray-600 dark:text-gray-300 whitespace-pre-wrap">
                  {{ deal.description }}
                </p>
              </div>

              <div
                v-if="deal.tags?.length"
                class="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700"
              >
                <h3 class="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                  Tags
                </h3>
                <div class="flex flex-wrap gap-1">
                  <span
                    v-for="tag in deal.tags"
                    :key="tag"
                    class="rounded-full bg-go4-primary/10 px-2 py-0.5 text-xs text-go4-primary"
                  >
                    {{ tag }}
                  </span>
                </div>
              </div>
            </div>
          </template>

          <!-- Activities Tab -->
          <template v-else-if="activeTab === 'activities'">
            <ActivityTimeline
              :activities="activities"
              :loading="activitiesLoading"
              @add="addActivity"
            />
          </template>

          <!-- Tasks Tab -->
          <template v-else-if="activeTab === 'tasks'">
            <TaskList
              :tasks="dealTasks"
              :deal-id="dealId"
            />
          </template>
        </div>

        <!-- Sidebar -->
        <div class="space-y-6">
          <!-- Contact Info -->
          <div
            v-if="contact"
            class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
          >
            <h3 class="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3">
              Kontakt
            </h3>
            <div class="flex items-center gap-3">
              <div
                class="flex h-10 w-10 items-center justify-center rounded-full bg-go4-primary/10 text-sm font-medium text-go4-primary"
              >
                {{
                  contact.name
                    ?.split(' ')
                    .map((n) => n[0])
                    .join('')
                    .slice(0, 2)
                    .toUpperCase()
                }}
              </div>
              <div>
                <div class="font-medium text-gray-900 dark:text-gray-100">
                  {{ contact.name }}
                </div>
                <div class="text-sm text-gray-500 dark:text-gray-400">
                  {{ contact.email }}
                </div>
              </div>
            </div>
          </div>

          <!-- Company Info -->
          <div
            v-if="company"
            class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
          >
            <h3 class="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3">
              Firma
            </h3>
            <div class="flex items-center gap-3">
              <div
                class="flex h-10 w-10 items-center justify-center rounded-full bg-gray-100 dark:bg-gray-700 text-sm font-medium text-gray-600 dark:text-gray-300"
              >
                {{ company.name?.[0]?.toUpperCase() }}
              </div>
              <div>
                <div class="font-medium text-gray-900 dark:text-gray-100">
                  {{ company.name }}
                </div>
                <div
                  v-if="company.website"
                  class="text-sm text-gray-500 dark:text-gray-400"
                >
                  {{ company.website }}
                </div>
              </div>
            </div>
          </div>

          <!-- Quick Stats -->
          <div
            class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
          >
            <h3 class="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3">
              Aktivität
            </h3>
            <dl class="space-y-2">
              <div class="flex justify-between text-sm">
                <dt class="text-gray-500 dark:text-gray-400">
                  Aktivitäten
                </dt>
                <dd class="font-medium text-gray-900 dark:text-gray-100">
                  {{ activities.length }}
                </dd>
              </div>
              <div class="flex justify-between text-sm">
                <dt class="text-gray-500 dark:text-gray-400">
                  Offene Tasks
                </dt>
                <dd class="font-medium text-gray-900 dark:text-gray-100">
                  {{ dealTasks.filter((t) => t.status === 'open').length }}
                </dd>
              </div>
            </dl>
          </div>
        </div>
      </div>
    </template>

    <!-- Edit Modal -->
    <DealFormModal
      :open="showEditModal"
      :deal="deal"
      :pipeline="pipeline"
      :default-stage-id="deal?.stage_id"
      :contacts="contactsStore.contacts"
      :companies="contactsStore.companies"
      :loading="modalLoading"
      @close="showEditModal = false"
      @save="saveDeal"
    />

    <!-- Delete Confirmation -->
    <ConfirmDialog
      :open="showDeleteDialog"
      title="Deal löschen"
      message="Möchten Sie diesen Deal wirklich löschen? Diese Aktion kann nicht rückgängig gemacht werden."
      confirm-text="Löschen"
      @confirm="deleteDeal"
      @cancel="showDeleteDialog = false"
    />
  </div>
</template>
