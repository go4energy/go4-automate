<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useContactsStore } from '@/stores/contacts'
import PageHeader from '@/components/ui/PageHeader.vue'
import SearchInput from '@/components/ui/SearchInput.vue'
import ViewModeToggle from '@/components/ui/ViewModeToggle.vue'
import FilterSidebar from '@/components/ui/FilterSidebar.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import DataTable from '@/components/ui/DataTable.vue'
import ContactCard from '@/components/contacts/ContactCard.vue'
import CompanyCard from '@/components/contacts/CompanyCard.vue'
import ContactFormModal from '@/components/contacts/ContactFormModal.vue'
import CompanyFormModal from '@/components/contacts/CompanyFormModal.vue'

const router = useRouter()
const route = useRoute()
const store = useContactsStore()

// Tab state from route
const activeTab = computed(() => route.meta?.tab || 'contacts')

// View mode
const viewMode = ref('cards')
const viewModes = [
  { value: 'cards', icon: 'cards', label: 'Karten' },
  { value: 'table', icon: 'table', label: 'Tabelle' }
]

// Search and filters
const searchQuery = ref('')
const activeFilters = ref({})

// Modal state
const showContactModal = ref(false)
const editingContact = ref(null)
const modalLoading = ref(false)

// Company modal state
const showCompanyModal = ref(false)
const editingCompany = ref(null)
const companyModalLoading = ref(false)

// Selection state
const selectedIds = ref([])

const tabs = [
  {
    key: 'contacts',
    label: 'Kontakte',
    route: '/contacts/people',
    count: computed(() => store.totalContacts)
  },
  {
    key: 'companies',
    label: 'Firmen',
    route: '/contacts/companies',
    count: computed(() => store.totalCompanies)
  }
]

// Contact table columns
const contactColumns = [
  { key: 'name', label: 'Name', sortable: true },
  { key: 'email', label: 'E-Mail', sortable: true },
  { key: 'company_name', label: 'Firma', sortable: true },
  { key: 'position', label: 'Position', sortable: false },
  { key: 'phone', label: 'Telefon', sortable: false },
  { key: 'source', label: 'Quelle', sortable: true }
]

// Company table columns
const companyColumns = [
  { key: 'name', label: 'Name', sortable: true },
  { key: 'domain', label: 'Domain', sortable: true },
  { key: 'industry', label: 'Branche', sortable: true },
  { key: 'size', label: 'Größe', sortable: false },
  { key: 'contact_count', label: 'Kontakte', sortable: true }
]

// Computed filter definitions
const contactFilters = computed(() => [
  {
    key: 'tags',
    label: 'Tags',
    multiple: true,
    options: (store.filterOptions.tags || []).map((t) => ({ value: t, label: t }))
  },
  {
    key: 'source',
    label: 'Quelle',
    multiple: false,
    options: (store.filterOptions.sources || []).map((s) => ({ value: s, label: s }))
  }
])

const companyFilters = computed(() => [
  {
    key: 'tags',
    label: 'Tags',
    multiple: true,
    options: (store.filterOptions.tags || []).map((t) => ({ value: t, label: t }))
  },
  {
    key: 'industry',
    label: 'Branche',
    multiple: false,
    options: [] // Could be populated from API
  }
])

const currentFilters = computed(() =>
  activeTab.value === 'contacts' ? contactFilters.value : companyFilters.value
)

onMounted(async () => {
  await loadData()
})

watch(activeTab, async () => {
  searchQuery.value = ''
  activeFilters.value = {}
  selectedIds.value = []
  await loadData()
})

watch([searchQuery, activeFilters], async () => {
  await loadData()
})

async function loadData() {
  // The list views are filterable + searchable in-page, so we pull a
  // big-enough page in one shot. Backend caps at 10000.
  const params = { limit: 10000 }
  if (searchQuery.value) {
    params.search = searchQuery.value
  }
  if (activeFilters.value.tags?.length) {
    params.tags = activeFilters.value.tags.join(',')
  }
  if (activeFilters.value.source) {
    params.source = activeFilters.value.source
  }
  if (activeFilters.value.industry) {
    params.industry = activeFilters.value.industry
  }

  if (activeTab.value === 'contacts') {
    await store.fetchContacts(params)
    await store.fetchFilters()
    // Also load companies for the form dropdown (smaller subset is fine)
    await store.fetchCompanies({ limit: 10000 })
  } else {
    await store.fetchCompanies(params)
  }
}

function onSearch(query) {
  searchQuery.value = query
}

// Contact actions
function openNewContactModal() {
  editingContact.value = null
  showContactModal.value = true
}

function openEditContactModal(contact) {
  editingContact.value = contact
  showContactModal.value = true
}

async function saveContact(data) {
  modalLoading.value = true
  try {
    if (editingContact.value) {
      await store.editContact(editingContact.value.id, data)
    } else {
      await store.addContact(data)
    }
    showContactModal.value = false
    await loadData()
  } catch {
    // Error is set in store
  } finally {
    modalLoading.value = false
  }
}

function goToContact(contact) {
  router.push({ name: 'contact-detail', params: { id: contact.id } })
}

function goToCompany(company) {
  router.push({ name: 'company-detail', params: { id: company.id } })
}

// Company actions
function openNewCompanyModal() {
  editingCompany.value = null
  showCompanyModal.value = true
}

async function saveCompany(data) {
  companyModalLoading.value = true
  try {
    if (editingCompany.value) {
      await store.editCompany(editingCompany.value.id, data)
    } else {
      await store.addCompany(data)
    }
    showCompanyModal.value = false
    await loadData()
  } catch {
    // Error is set in store
  } finally {
    companyModalLoading.value = false
  }
}

function emailContact(contact) {
  window.location.href = `mailto:${contact.email}`
}

function callContact(contact) {
  window.location.href = `tel:${contact.phone}`
}

// Bulk actions
async function deleteSelected() {
  if (selectedIds.value.length === 0) return
  if (!confirm(`${selectedIds.value.length} Kontakte löschen?`)) return

  try {
    await store.bulkDelete(selectedIds.value)
    selectedIds.value = []
  } catch {
    // Error is set in store
  }
}

function onSelect({ id, selected }) {
  if (selected) {
    selectedIds.value = [...selectedIds.value, id]
  } else {
    selectedIds.value = selectedIds.value.filter((i) => i !== id)
  }
}

function onSelectAll(selected) {
  if (selected) {
    const items = activeTab.value === 'contacts' ? store.contacts : store.companies
    selectedIds.value = items.map((item) => item.id)
  } else {
    selectedIds.value = []
  }
}

function onRowClick(row) {
  if (activeTab.value === 'contacts') {
    goToContact(row)
  } else {
    goToCompany(row)
  }
}

function onSort({ key, direction }) {
  const prefix = direction === 'desc' ? '-' : ''
  const params = { sort: `${prefix}${key}` }
  if (searchQuery.value) params.search = searchQuery.value
  if (activeTab.value === 'contacts') {
    store.fetchContacts(params)
  } else {
    store.fetchCompanies(params)
  }
}

function formatDate(dateString) {
  return new Date(dateString).toLocaleDateString('de-DE')
}
</script>

<template>
  <div>
    <PageHeader
      title="Kontakte"
    >
      <template #actions>
        <button
          v-if="activeTab === 'contacts'"
          type="button"
          class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark"
          @click="openNewContactModal"
        >
          + Kontakt
        </button>
        <button
          v-if="activeTab === 'companies'"
          type="button"
          class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark"
          @click="openNewCompanyModal"
        >
          + Firma
        </button>
      </template>
    </PageHeader>

    <!-- Tabs + Search + View Toggle -->
    <div class="mt-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div class="flex gap-1 border-b border-gray-200 dark:border-gray-700">
        <router-link
          v-for="tab in tabs"
          :key="tab.key"
          :to="tab.route"
          class="px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors"
          :class="
            activeTab === tab.key
              ? 'border-go4-primary text-go4-primary'
              : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
          "
        >
          {{ tab.label }}
          <span class="ml-1 rounded-full bg-gray-100 dark:bg-gray-700 px-2 py-0.5 text-xs">
            {{ tab.count.value }}
          </span>
        </router-link>
      </div>

      <div class="flex items-center gap-3">
        <SearchInput
          v-model="searchQuery"
          placeholder="Suchen..."
          class="w-64"
          @search="onSearch"
        />
        <ViewModeToggle
          v-model="viewMode"
          :modes="viewModes"
        />
      </div>
    </div>

    <!-- Bulk Actions Bar -->
    <div
      v-if="selectedIds.length > 0"
      class="mt-4 flex items-center gap-4 rounded-lg bg-go4-primary/10 px-4 py-2"
    >
      <span class="text-sm font-medium text-go4-primary">
        {{ selectedIds.length }} ausgewählt
      </span>
      <button
        type="button"
        class="rounded bg-red-100 px-3 py-1 text-sm text-red-700 hover:bg-red-200"
        @click="deleteSelected"
      >
        Löschen
      </button>
      <button
        type="button"
        class="text-sm text-gray-500 hover:text-gray-700"
        @click="selectedIds = []"
      >
        Auswahl aufheben
      </button>
    </div>

    <!-- Main Content -->
    <div class="mt-6 flex gap-6">
      <!-- Filter Sidebar -->
      <FilterSidebar
        v-if="currentFilters.length > 0 && currentFilters.some((f) => f.options.length > 0)"
        v-model="activeFilters"
        :filters="currentFilters"
      />

      <!-- Content Area -->
      <div class="flex-1">
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

        <!-- Contacts Tab -->
        <template v-else-if="activeTab === 'contacts'">
          <EmptyState
            v-if="store.contacts.length === 0"
            title="Keine Kontakte"
          >
            <template #action>
              <button
                type="button"
                class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark"
                @click="openNewContactModal"
              >
                + Kontakt erstellen
              </button>
            </template>
          </EmptyState>

          <!-- Cards View -->
          <div
            v-else-if="viewMode === 'cards'"
            class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"
          >
            <ContactCard
              v-for="contact in store.contacts"
              :key="contact.id"
              :contact="contact"
              @click="goToContact"
              @email="emailContact"
              @call="callContact"
            />
          </div>

          <!-- Table View -->
          <DataTable
            v-else
            :columns="contactColumns"
            :data="store.contacts"
            :selectable="true"
            :selected-ids="selectedIds"
            @select="onSelect"
            @select-all="onSelectAll"
            @row-click="onRowClick"
            @sort="onSort"
          >
            <template #cell-name="{ row }">
              <div class="flex items-center gap-2">
                <div
                  class="h-8 w-8 rounded-full bg-go4-primary flex items-center justify-center text-white text-xs font-medium"
                >
                  {{
                    row.name
                      .split(' ')
                      .map((n) => n[0])
                      .join('')
                      .slice(0, 2)
                      .toUpperCase()
                  }}
                </div>
                <span class="font-medium">{{ row.name }}</span>
              </div>
            </template>
            <template #cell-source="{ value }">
              <span
                v-if="value"
                class="inline-flex rounded-full bg-gray-100 dark:bg-gray-700 px-2 py-0.5 text-xs"
              >
                {{ value }}
              </span>
              <span
                v-else
                class="text-gray-400"
              >-</span>
            </template>
          </DataTable>
        </template>

        <!-- Companies Tab -->
        <template v-else-if="activeTab === 'companies'">
          <EmptyState
            v-if="store.companies.length === 0"
            title="Keine Firmen"
          />

          <!-- Cards View -->
          <div
            v-else-if="viewMode === 'cards'"
            class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"
          >
            <CompanyCard
              v-for="company in store.companies"
              :key="company.id"
              :company="company"
              @click="goToCompany"
            />
          </div>

          <!-- Table View -->
          <DataTable
            v-else
            :columns="companyColumns"
            :data="store.companies"
            @row-click="onRowClick"
            @sort="onSort"
          >
            <template #cell-name="{ row }">
              <div class="flex items-center gap-2">
                <div
                  class="h-8 w-8 rounded-lg bg-indigo-500 flex items-center justify-center text-white text-xs font-medium"
                >
                  {{ row.name.slice(0, 2).toUpperCase() }}
                </div>
                <span class="font-medium">{{ row.name }}</span>
              </div>
            </template>
            <template #cell-contact_count="{ value }">
              <span class="text-gray-600 dark:text-gray-400">{{ value }}</span>
            </template>
          </DataTable>
        </template>
      </div>
    </div>

    <!-- Contact Form Modal -->
    <ContactFormModal
      :open="showContactModal"
      :contact="editingContact"
      :companies="store.companies"
      :loading="modalLoading"
      @close="showContactModal = false"
      @save="saveContact"
    />

    <!-- Company Form Modal -->
    <CompanyFormModal
      :open="showCompanyModal"
      :company="editingCompany"
      :loading="companyModalLoading"
      @close="showCompanyModal = false"
      @save="saveCompany"
    />
  </div>
</template>
