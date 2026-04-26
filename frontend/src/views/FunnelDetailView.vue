<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useFunnelsStore } from '@/stores/funnels'
import { useTabState } from '@/composables/useTabState'
import PageHeader from '@/components/ui/PageHeader.vue'
import SearchInput from '@/components/ui/SearchInput.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import DataTable from '@/components/ui/DataTable.vue'
import ProspectCard from '@/components/funnels/ProspectCard.vue'
import StageEditor from '@/components/funnels/StageEditor.vue'

const route = useRoute()
const router = useRouter()
const store = useFunnelsStore()

const funnelId = computed(() => Number(route.params.id))
const activeTab = useTabState('funnel-detail', 'overview', [
  'overview',
  'companies',
  'prospects',
  'settings'
])

// Filters
const searchQuery = ref('')
const stageFilter = ref('')
const statusFilter = ref('')
const selectedItems = ref([])

// Modals
const showCompanyModal = ref(false)
const showProspectModal = ref(false)
const showEditModal = ref(false)
const showDeleteConfirm = ref(false)
const deleteTarget = ref(null)
const deleteType = ref('')

// Form data
const companyForm = ref({
  name: '',
  domain: '',
  website: '',
  industry: '',
  size: '',
  phone: '',
  email: '',
  tags: []
})
const prospectForm = ref({
  name: '',
  email: '',
  phone: '',
  position: '',
  company_id: null,
  stage_id: null,
  tags: []
})
const funnelForm = ref({
  name: '',
  description: '',
  color: '#8B5CF6',
  status: 'active',
  tags: []
})
const formLoading = ref(false)

const colors = [
  '#8B5CF6',
  '#3B82F6',
  '#10B981',
  '#F59E0B',
  '#EF4444',
  '#EC4899',
  '#6366F1',
  '#14B8A6'
]

const funnel = computed(() => store.currentFunnel)
const stages = computed(() => store.stages)
const companies = computed(() => store.companies)
const prospects = computed(() => store.prospects)

const filteredCompanies = computed(() => {
  let result = companies.value

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(
      (c) =>
        c.name.toLowerCase().includes(query) ||
        c.domain?.toLowerCase().includes(query) ||
        c.industry?.toLowerCase().includes(query)
    )
  }

  return result
})

const filteredProspects = computed(() => {
  let result = prospects.value

  if (stageFilter.value) {
    result = result.filter((p) => p.stage_id === Number(stageFilter.value))
  }

  if (statusFilter.value) {
    result = result.filter((p) => p.status === statusFilter.value)
  }

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(
      (p) =>
        p.name.toLowerCase().includes(query) ||
        p.email?.toLowerCase().includes(query) ||
        p.company_name?.toLowerCase().includes(query)
    )
  }

  return result
})

const stats = computed(() => {
  const total = prospects.value.length
  const qualified = prospects.value.filter((p) => p.status === 'qualified').length
  const handedOff = prospects.value.filter((p) => p.status === 'handed_off').length
  const avgScore =
    total > 0 ? Math.round(prospects.value.reduce((sum, p) => sum + (p.score || 0), 0) / total) : 0

  return { total, qualified, handedOff, avgScore }
})

const companyColumns = [
  { key: 'name', label: 'Name', sortable: true },
  { key: 'domain', label: 'Domain', sortable: true },
  { key: 'industry', label: 'Branche', sortable: true },
  { key: 'prospect_count', label: 'Prospects', sortable: true },
  { key: 'actions', label: '', width: '100px' }
]

onMounted(async () => {
  await loadFunnel()
})

watch(funnelId, async () => {
  await loadFunnel()
})

async function loadFunnel() {
  await store.fetchFunnel(funnelId.value)
  await Promise.all([
    store.fetchStages(funnelId.value),
    store.fetchCompanies(funnelId.value),
    store.fetchProspects(funnelId.value)
  ])
}

function openKanban() {
  router.push(`/funnels/${funnelId.value}/kanban`)
}

function openProspect(prospect) {
  router.push(`/funnels/prospects/${prospect.id}`)
}

function openCompanyModal() {
  companyForm.value = {
    name: '',
    domain: '',
    website: '',
    industry: '',
    size: '',
    phone: '',
    email: '',
    tags: []
  }
  showCompanyModal.value = true
}

function openProspectModal() {
  prospectForm.value = {
    name: '',
    email: '',
    phone: '',
    position: '',
    company_id: null,
    stage_id: stages.value[0]?.id || null,
    tags: []
  }
  showProspectModal.value = true
}

function openEditModal() {
  funnelForm.value = {
    name: funnel.value.name,
    description: funnel.value.description || '',
    color: funnel.value.color || '#8B5CF6',
    status: funnel.value.status,
    tags: funnel.value.tags || []
  }
  showEditModal.value = true
}

async function createCompany() {
  if (!companyForm.value.name.trim()) return

  formLoading.value = true
  try {
    await store.addCompany(funnelId.value, companyForm.value)
    showCompanyModal.value = false
  } finally {
    formLoading.value = false
  }
}

async function createProspect() {
  if (!prospectForm.value.name.trim() || !prospectForm.value.email.trim()) return

  formLoading.value = true
  try {
    const prospect = await store.addProspect(funnelId.value, prospectForm.value)
    showProspectModal.value = false
    router.push(`/funnels/prospects/${prospect.id}`)
  } finally {
    formLoading.value = false
  }
}

async function updateFunnel() {
  if (!funnelForm.value.name.trim()) return

  formLoading.value = true
  try {
    await store.editFunnel(funnelId.value, funnelForm.value)
    showEditModal.value = false
  } finally {
    formLoading.value = false
  }
}

function confirmDeleteCompany(company) {
  deleteTarget.value = company
  deleteType.value = 'company'
  showDeleteConfirm.value = true
}

function confirmDeleteFunnel() {
  deleteTarget.value = funnel.value
  deleteType.value = 'funnel'
  showDeleteConfirm.value = true
}

async function executeDelete() {
  if (!deleteTarget.value) return

  try {
    if (deleteType.value === 'company') {
      await store.removeCompany(deleteTarget.value.id)
    } else if (deleteType.value === 'funnel') {
      await store.removeFunnel(funnelId.value)
      router.push('/funnels')
    }
    showDeleteConfirm.value = false
    deleteTarget.value = null
  } catch {
    // Error is in store
  }
}

async function addStage(stageData) {
  await store.addStage(funnelId.value, stageData)
}

async function updateStage(stageId, stageData) {
  await store.editStage(stageId, stageData)
}

async function deleteStage(stageId) {
  await store.removeStage(stageId)
}

function getStatusLabel(status) {
  const labels = {
    active: 'Aktiv',
    paused: 'Pausiert',
    archived: 'Archiviert'
  }
  return labels[status] || status
}

function getStatusColor(status) {
  const colors = {
    active: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    paused: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
    archived: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
  }
  return colors[status] || colors.archived
}
</script>

<template>
  <div class="min-h-screen bg-go4-bg dark:bg-gray-900">
    <!-- Loading -->
    <div
      v-if="store.loading"
      class="flex items-center justify-center py-24"
    >
      <span class="text-go4-muted dark:text-gray-400">Laden...</span>
    </div>

    <!-- Error -->
    <div
      v-else-if="store.error"
      class="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8"
    >
      <div class="rounded-lg bg-red-50 p-4 text-red-700 dark:bg-red-900/30 dark:text-red-300">
        {{ store.error }}
      </div>
    </div>

    <!-- Content -->
    <template v-else-if="funnel">
      <PageHeader
        :title="funnel.name"
        :subtitle="funnel.description || 'Funnel'"
      >
        <template #actions>
          <button
            class="flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700"
            @click="openKanban"
          >
            <svg
              class="h-5 w-5"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                d="M5 3a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2V5a2 2 0 00-2-2H5zM5 11a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2v-2a2 2 0 00-2-2H5zM11 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V5zM11 13a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"
              />
            </svg>
            Kanban
          </button>
          <button
            class="flex items-center gap-2 rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark"
            @click="openProspectModal"
          >
            <svg
              class="h-5 w-5"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fill-rule="evenodd"
                d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
                clip-rule="evenodd"
              />
            </svg>
            Neuer Prospect
          </button>
        </template>
      </PageHeader>

      <div class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <!-- Tabs -->
        <div class="mb-6 border-b border-gray-200 dark:border-gray-700">
          <nav class="-mb-px flex gap-6">
            <button
              v-for="tab in [
                { id: 'overview', label: 'Uebersicht' },
                { id: 'companies', label: 'Firmen' },
                { id: 'prospects', label: 'Prospects' },
                { id: 'settings', label: 'Einstellungen' }
              ]"
              :key="tab.id"
              class="border-b-2 pb-3 text-sm font-medium transition-colors"
              :class="{
                'border-go4-primary text-go4-primary': activeTab === tab.id,
                'border-transparent text-go4-muted hover:border-gray-300 hover:text-go4-secondary dark:text-gray-400 dark:hover:text-white':
                  activeTab !== tab.id
              }"
              @click="activeTab = tab.id"
            >
              {{ tab.label }}
            </button>
          </nav>
        </div>

        <!-- Overview Tab -->
        <div
          v-if="activeTab === 'overview'"
          class="space-y-6"
        >
          <!-- Stats Grid -->
          <div class="grid grid-cols-2 gap-4 md:grid-cols-4">
            <div class="rounded-lg bg-white dark:bg-gray-800 p-4 shadow-sm">
              <div class="text-2xl font-bold text-go4-secondary dark:text-white">
                {{ stats.total }}
              </div>
              <div class="text-sm text-go4-muted dark:text-gray-400">
                Prospects
              </div>
            </div>
            <div class="rounded-lg bg-white dark:bg-gray-800 p-4 shadow-sm">
              <div class="text-2xl font-bold text-go4-secondary dark:text-white">
                {{ companies.length }}
              </div>
              <div class="text-sm text-go4-muted dark:text-gray-400">
                Firmen
              </div>
            </div>
            <div class="rounded-lg bg-white dark:bg-gray-800 p-4 shadow-sm">
              <div class="text-2xl font-bold text-green-600">
                {{ stats.qualified }}
              </div>
              <div class="text-sm text-go4-muted dark:text-gray-400">
                Qualifiziert
              </div>
            </div>
            <div class="rounded-lg bg-white dark:bg-gray-800 p-4 shadow-sm">
              <div class="text-2xl font-bold text-teal-600">
                {{ stats.handedOff }}
              </div>
              <div class="text-sm text-go4-muted dark:text-gray-400">
                Uebergeben
              </div>
            </div>
          </div>

          <!-- Stage Overview -->
          <div class="rounded-lg bg-white dark:bg-gray-800 p-6 shadow-sm">
            <h3 class="mb-4 text-lg font-semibold text-go4-secondary dark:text-white">
              Stages
            </h3>
            <div class="flex gap-2 overflow-x-auto pb-2">
              <div
                v-for="stage in stages"
                :key="stage.id"
                class="flex min-w-[120px] flex-col items-center rounded-lg border border-gray-200 dark:border-gray-700 p-3"
              >
                <div
                  class="mb-2 h-3 w-3 rounded-full"
                  :style="{ backgroundColor: stage.color }"
                />
                <span class="text-sm font-medium text-go4-secondary dark:text-white">
                  {{ stage.name }}
                </span>
                <span class="text-xl font-bold text-go4-secondary dark:text-white">
                  {{ stage.prospect_count || 0 }}
                </span>
              </div>
            </div>
          </div>

          <!-- Recent Prospects -->
          <div class="rounded-lg bg-white dark:bg-gray-800 p-6 shadow-sm">
            <div class="mb-4 flex items-center justify-between">
              <h3 class="text-lg font-semibold text-go4-secondary dark:text-white">
                Neueste Prospects
              </h3>
              <button
                class="text-sm text-go4-primary hover:underline"
                @click="activeTab = 'prospects'"
              >
                Alle anzeigen
              </button>
            </div>
            <div
              v-if="prospects.length === 0"
              class="py-8 text-center text-go4-muted"
            >
              Noch keine Prospects
            </div>
            <div
              v-else
              class="grid gap-3 md:grid-cols-2 lg:grid-cols-3"
            >
              <ProspectCard
                v-for="prospect in prospects.slice(0, 6)"
                :key="prospect.id"
                :prospect="prospect"
                compact
                @click="openProspect"
              />
            </div>
          </div>
        </div>

        <!-- Companies Tab -->
        <div
          v-else-if="activeTab === 'companies'"
          class="space-y-4"
        >
          <div class="flex flex-wrap items-center gap-4">
            <SearchInput
              v-model="searchQuery"
              placeholder="Firmen suchen..."
              class="w-64"
            />
            <button
              class="ml-auto flex items-center gap-2 rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark"
              @click="openCompanyModal"
            >
              <svg
                class="h-5 w-5"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fill-rule="evenodd"
                  d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
                  clip-rule="evenodd"
                />
              </svg>
              Neue Firma
            </button>
          </div>

          <EmptyState
            v-if="filteredCompanies.length === 0"
            title="Keine Firmen"
            description="Fuege deine erste Firma hinzu."
          >
            <button
              class="mt-4 rounded-lg bg-go4-primary px-4 py-2 text-sm text-white hover:bg-go4-primary-dark"
              @click="openCompanyModal"
            >
              Firma erstellen
            </button>
          </EmptyState>

          <DataTable
            v-else
            v-model:selected="selectedItems"
            :columns="companyColumns"
            :data="filteredCompanies"
            :selectable="true"
          >
            <template #cell-name="{ row }">
              <span class="font-medium text-go4-secondary dark:text-white">
                {{ row.name }}
              </span>
            </template>
            <template #cell-actions="{ row }">
              <div class="flex gap-1">
                <button
                  class="rounded p-1 text-gray-400 hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-900"
                  @click="confirmDeleteCompany(row)"
                >
                  <svg
                    class="h-4 w-4"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fill-rule="evenodd"
                      d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"
                      clip-rule="evenodd"
                    />
                  </svg>
                </button>
              </div>
            </template>
          </DataTable>
        </div>

        <!-- Prospects Tab -->
        <div
          v-else-if="activeTab === 'prospects'"
          class="space-y-4"
        >
          <div class="flex flex-wrap items-center gap-4">
            <SearchInput
              v-model="searchQuery"
              placeholder="Prospects suchen..."
              class="w-64"
            />

            <select
              v-model="stageFilter"
              class="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
            >
              <option value="">
                Alle Stages
              </option>
              <option
                v-for="stage in stages"
                :key="stage.id"
                :value="stage.id"
              >
                {{ stage.name }}
              </option>
            </select>

            <select
              v-model="statusFilter"
              class="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
            >
              <option value="">
                Alle Status
              </option>
              <option value="new">
                Neu
              </option>
              <option value="contacted">
                Kontaktiert
              </option>
              <option value="engaged">
                Interessiert
              </option>
              <option value="qualified">
                Qualifiziert
              </option>
              <option value="handed_off">
                Uebergeben
              </option>
            </select>

            <span class="ml-auto text-sm text-go4-muted dark:text-gray-400">
              {{ filteredProspects.length }} Prospects
            </span>
          </div>

          <EmptyState
            v-if="filteredProspects.length === 0"
            title="Keine Prospects"
            description="Fuege deinen ersten Prospect hinzu."
          >
            <button
              class="mt-4 rounded-lg bg-go4-primary px-4 py-2 text-sm text-white hover:bg-go4-primary-dark"
              @click="openProspectModal"
            >
              Prospect erstellen
            </button>
          </EmptyState>

          <div
            v-else
            class="grid gap-4 md:grid-cols-2 lg:grid-cols-3"
          >
            <ProspectCard
              v-for="prospect in filteredProspects"
              :key="prospect.id"
              :prospect="prospect"
              @click="openProspect"
            />
          </div>
        </div>

        <!-- Settings Tab -->
        <div
          v-else-if="activeTab === 'settings'"
          class="space-y-6"
        >
          <!-- Funnel Info -->
          <div class="rounded-lg bg-white dark:bg-gray-800 p-6 shadow-sm">
            <div class="mb-4 flex items-center justify-between">
              <h3 class="text-lg font-semibold text-go4-secondary dark:text-white">
                Funnel Informationen
              </h3>
              <button
                class="flex items-center gap-1 text-sm text-go4-primary hover:underline"
                @click="openEditModal"
              >
                <svg
                  class="h-4 w-4"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path
                    d="M17.414 2.586a2 2 0 00-2.828 0L7 10.172V13h2.828l7.586-7.586a2 2 0 000-2.828z"
                  />
                </svg>
                Bearbeiten
              </button>
            </div>
            <dl class="grid gap-4 sm:grid-cols-2">
              <div>
                <dt class="text-sm text-go4-muted dark:text-gray-400">
                  Name
                </dt>
                <dd class="font-medium text-go4-secondary dark:text-white">
                  {{ funnel.name }}
                </dd>
              </div>
              <div>
                <dt class="text-sm text-go4-muted dark:text-gray-400">
                  Status
                </dt>
                <dd>
                  <span
                    class="inline-flex rounded-full px-2 py-0.5 text-xs font-medium"
                    :class="getStatusColor(funnel.status)"
                  >
                    {{ getStatusLabel(funnel.status) }}
                  </span>
                </dd>
              </div>
              <div>
                <dt class="text-sm text-go4-muted dark:text-gray-400">
                  Farbe
                </dt>
                <dd class="flex items-center gap-2">
                  <div
                    class="h-4 w-4 rounded-full"
                    :style="{ backgroundColor: funnel.color }"
                  />
                  <span class="text-sm text-go4-secondary dark:text-white">
                    {{ funnel.color }}
                  </span>
                </dd>
              </div>
              <div>
                <dt class="text-sm text-go4-muted dark:text-gray-400">
                  Erstellt
                </dt>
                <dd class="text-go4-secondary dark:text-white">
                  {{ new Date(funnel.created_at).toLocaleDateString('de-DE') }}
                </dd>
              </div>
            </dl>
          </div>

          <!-- Stages -->
          <div class="rounded-lg bg-white dark:bg-gray-800 p-6 shadow-sm">
            <h3 class="mb-4 text-lg font-semibold text-go4-secondary dark:text-white">
              Stages
            </h3>
            <StageEditor
              :stages="stages"
              @add="addStage"
              @update="updateStage"
              @delete="deleteStage"
            />
          </div>

          <!-- Danger Zone -->
          <div
            class="rounded-lg border border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20 p-6"
          >
            <h3 class="mb-2 text-lg font-semibold text-red-800 dark:text-red-200">
              Gefahrenzone
            </h3>
            <p class="mb-4 text-sm text-red-700 dark:text-red-300">
              Das Loeschen des Funnels entfernt alle Firmen, Prospects und Aktivitaeten.
            </p>
            <button
              class="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
              @click="confirmDeleteFunnel"
            >
              Funnel loeschen
            </button>
          </div>
        </div>
      </div>
    </template>

    <!-- Company Create Modal -->
    <Teleport to="body">
      <div
        v-if="showCompanyModal"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
        @click.self="showCompanyModal = false"
      >
        <div class="w-full max-w-lg rounded-lg bg-white dark:bg-gray-800 p-6 shadow-xl">
          <h2 class="mb-4 text-lg font-semibold text-go4-secondary dark:text-white">
            Neue Firma
          </h2>

          <form
            class="space-y-4"
            @submit.prevent="createCompany"
          >
            <div class="grid gap-4 sm:grid-cols-2">
              <div>
                <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                  Name *
                </label>
                <input
                  v-model="companyForm.name"
                  type="text"
                  required
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                >
              </div>
              <div>
                <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                  Domain
                </label>
                <input
                  v-model="companyForm.domain"
                  type="text"
                  placeholder="beispiel.de"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                >
              </div>
              <div>
                <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                  Branche
                </label>
                <input
                  v-model="companyForm.industry"
                  type="text"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                >
              </div>
              <div>
                <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                  Groesse
                </label>
                <select
                  v-model="companyForm.size"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                >
                  <option value="">
                    -- Auswaehlen --
                  </option>
                  <option value="1-10">
                    1-10
                  </option>
                  <option value="11-50">
                    11-50
                  </option>
                  <option value="51-200">
                    51-200
                  </option>
                  <option value="201-500">
                    201-500
                  </option>
                  <option value="501+">
                    501+
                  </option>
                </select>
              </div>
              <div>
                <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                  Telefon
                </label>
                <input
                  v-model="companyForm.phone"
                  type="tel"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                >
              </div>
              <div>
                <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                  E-Mail
                </label>
                <input
                  v-model="companyForm.email"
                  type="email"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                >
              </div>
            </div>

            <div class="flex justify-end gap-3 pt-4">
              <button
                type="button"
                class="rounded-lg px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
                @click="showCompanyModal = false"
              >
                Abbrechen
              </button>
              <button
                type="submit"
                class="rounded-lg bg-go4-primary px-4 py-2 text-sm text-white hover:bg-go4-primary-dark disabled:opacity-50"
                :disabled="formLoading || !companyForm.name.trim()"
              >
                {{ formLoading ? 'Erstellen...' : 'Erstellen' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Prospect Create Modal -->
    <Teleport to="body">
      <div
        v-if="showProspectModal"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
        @click.self="showProspectModal = false"
      >
        <div class="w-full max-w-lg rounded-lg bg-white dark:bg-gray-800 p-6 shadow-xl">
          <h2 class="mb-4 text-lg font-semibold text-go4-secondary dark:text-white">
            Neuer Prospect
          </h2>

          <form
            class="space-y-4"
            @submit.prevent="createProspect"
          >
            <div class="grid gap-4 sm:grid-cols-2">
              <div class="sm:col-span-2">
                <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                  Name *
                </label>
                <input
                  v-model="prospectForm.name"
                  type="text"
                  required
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                >
              </div>
              <div>
                <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                  E-Mail *
                </label>
                <input
                  v-model="prospectForm.email"
                  type="email"
                  required
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                >
              </div>
              <div>
                <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                  Telefon
                </label>
                <input
                  v-model="prospectForm.phone"
                  type="tel"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                >
              </div>
              <div>
                <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                  Position
                </label>
                <input
                  v-model="prospectForm.position"
                  type="text"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                >
              </div>
              <div>
                <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                  Firma
                </label>
                <select
                  v-model="prospectForm.company_id"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                >
                  <option :value="null">
                    -- Keine --
                  </option>
                  <option
                    v-for="company in companies"
                    :key="company.id"
                    :value="company.id"
                  >
                    {{ company.name }}
                  </option>
                </select>
              </div>
              <div>
                <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                  Stage
                </label>
                <select
                  v-model="prospectForm.stage_id"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                >
                  <option
                    v-for="stage in stages"
                    :key="stage.id"
                    :value="stage.id"
                  >
                    {{ stage.name }}
                  </option>
                </select>
              </div>
            </div>

            <div class="flex justify-end gap-3 pt-4">
              <button
                type="button"
                class="rounded-lg px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
                @click="showProspectModal = false"
              >
                Abbrechen
              </button>
              <button
                type="submit"
                class="rounded-lg bg-go4-primary px-4 py-2 text-sm text-white hover:bg-go4-primary-dark disabled:opacity-50"
                :disabled="formLoading || !prospectForm.name.trim() || !prospectForm.email.trim()"
              >
                {{ formLoading ? 'Erstellen...' : 'Erstellen' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Edit Funnel Modal -->
    <Teleport to="body">
      <div
        v-if="showEditModal"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
        @click.self="showEditModal = false"
      >
        <div class="w-full max-w-md rounded-lg bg-white dark:bg-gray-800 p-6 shadow-xl">
          <h2 class="mb-4 text-lg font-semibold text-go4-secondary dark:text-white">
            Funnel bearbeiten
          </h2>

          <form
            class="space-y-4"
            @submit.prevent="updateFunnel"
          >
            <div>
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                Name *
              </label>
              <input
                v-model="funnelForm.name"
                type="text"
                required
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
            </div>

            <div>
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                Beschreibung
              </label>
              <textarea
                v-model="funnelForm.description"
                rows="2"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              />
            </div>

            <div>
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                Status
              </label>
              <select
                v-model="funnelForm.status"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
                <option value="active">
                  Aktiv
                </option>
                <option value="paused">
                  Pausiert
                </option>
                <option value="archived">
                  Archiviert
                </option>
              </select>
            </div>

            <div>
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                Farbe
              </label>
              <div class="flex gap-2">
                <button
                  v-for="color in colors"
                  :key="color"
                  type="button"
                  class="h-8 w-8 rounded-full border-2 transition-transform hover:scale-110"
                  :class="{
                    'border-gray-800 dark:border-white': funnelForm.color === color,
                    'border-transparent': funnelForm.color !== color
                  }"
                  :style="{ backgroundColor: color }"
                  @click="funnelForm.color = color"
                />
              </div>
            </div>

            <div class="flex justify-end gap-3 pt-4">
              <button
                type="button"
                class="rounded-lg px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
                @click="showEditModal = false"
              >
                Abbrechen
              </button>
              <button
                type="submit"
                class="rounded-lg bg-go4-primary px-4 py-2 text-sm text-white hover:bg-go4-primary-dark disabled:opacity-50"
                :disabled="formLoading || !funnelForm.name.trim()"
              >
                {{ formLoading ? 'Speichern...' : 'Speichern' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Delete Confirmation -->
    <ConfirmDialog
      :open="showDeleteConfirm"
      :title="deleteType === 'funnel' ? 'Funnel loeschen?' : 'Firma loeschen?'"
      :message="
        deleteType === 'funnel'
          ? `Möchtest du den Funnel '${deleteTarget?.name}' wirklich löschen? Alle Firmen, Prospects und Aktivitäten werden ebenfalls gelöscht.`
          : `Möchtest du die Firma '${deleteTarget?.name}' wirklich löschen?`
      "
      confirm-text="Loeschen"
      variant="danger"
      @confirm="executeDelete"
      @cancel="showDeleteConfirm = false"
    />
  </div>
</template>
