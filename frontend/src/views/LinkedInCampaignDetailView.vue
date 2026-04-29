<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useLinkedInStore } from '@/stores/linkedin'
import PageHeader from '@/components/ui/PageHeader.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import SearchInput from '@/components/ui/SearchInput.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'

const router = useRouter()
const route = useRoute()
const store = useLinkedInStore()

const props = defineProps({
  id: { type: [String, Number], required: true }
})

const searchQuery = ref('')
const statusFilter = ref('')
const showAddLeadsModal = ref(false)
const showRemoveLeadConfirm = ref(false)
const leadToRemove = ref(null)
const selectedContacts = ref([])
const addingLeads = ref(false)

const statusColors = {
  pending: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
  active: 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300',
  completed: 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300',
  replied: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300',
  stopped: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-300',
  failed: 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300'
}

const statusLabels = {
  pending: 'Wartend',
  active: 'Aktiv',
  completed: 'Abgeschlossen',
  replied: 'Antwort erhalten',
  stopped: 'Gestoppt',
  failed: 'Fehlgeschlagen'
}

const stepTypeLabels = {
  connect: 'Kontaktanfrage',
  message: 'Nachricht',
  wait: 'Warten',
  condition: 'Bedingung'
}

const campaign = computed(() => store.currentCampaign)

const filteredLeads = computed(() => {
  let result = store.campaignLeads
  if (statusFilter.value) {
    result = result.filter((l) => l.status === statusFilter.value)
  }
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter(
      (l) =>
        l.contact_name?.toLowerCase().includes(q) || l.contact_company?.toLowerCase().includes(q)
    )
  }
  return result
})

const availableContacts = computed(() => {
  const leadContactIds = new Set(store.campaignLeads.map((l) => l.contact_id))
  return store.contacts.filter((c) => !leadContactIds.has(c.id))
})

const stats = computed(() => {
  const leads = store.campaignLeads
  return {
    total: leads.length,
    pending: leads.filter((l) => l.status === 'pending').length,
    active: leads.filter((l) => l.status === 'active').length,
    completed: leads.filter((l) => l.status === 'completed').length,
    replied: leads.filter((l) => l.status === 'replied').length,
    stopped: leads.filter((l) => l.status === 'stopped').length,
    failed: leads.filter((l) => l.status === 'failed').length
  }
})

onMounted(async () => {
  await Promise.all([
    store.fetchCampaign(props.id),
    store.fetchCampaignLeads(props.id),
    store.fetchAllContacts()
  ])
})

function editCampaign() {
  router.push(`/linkedin/campaigns/${props.id}/edit`)
}

async function startCampaign() {
  try {
    await store.runCampaign(props.id)
  } catch {
    // Error handled in store
  }
}

async function pauseCampaign() {
  try {
    await store.stopCampaign(props.id)
  } catch {
    // Error handled in store
  }
}

function openAddLeads() {
  selectedContacts.value = []
  showAddLeadsModal.value = true
}

function toggleContact(contactId) {
  const index = selectedContacts.value.indexOf(contactId)
  if (index === -1) {
    selectedContacts.value.push(contactId)
  } else {
    selectedContacts.value.splice(index, 1)
  }
}

async function addSelectedLeads() {
  if (selectedContacts.value.length === 0) return

  addingLeads.value = true
  try {
    await store.addLeadsToCampaignBulk(props.id, selectedContacts.value)
    showAddLeadsModal.value = false
    selectedContacts.value = []
  } catch {
    // Error handled in store
  } finally {
    addingLeads.value = false
  }
}

function confirmRemoveLead(lead) {
  leadToRemove.value = lead
  showRemoveLeadConfirm.value = true
}

async function removeLead() {
  if (!leadToRemove.value) return
  try {
    await store.removeLeadFromCampaign(props.id, leadToRemove.value.id)
    showRemoveLeadConfirm.value = false
    leadToRemove.value = null
  } catch {
    // Error handled in store
  }
}

async function stopLead(lead) {
  try {
    await store.pauseLeadInCampaign(props.id, lead.id)
  } catch {
    // Error handled in store
  }
}

function openContact(lead) {
  router.push(`/linkedin/contacts/${lead.contact_id}`)
}
</script>

<template>
  <div class="bg-go4-bg dark:bg-gray-900">
    <PageHeader
      :title="campaign?.name || 'Kampagne'"
    >
      <template #actions>
        <button
          v-if="campaign?.status === 'draft' || campaign?.status === 'paused'"
          class="flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700"
          @click="startCampaign"
        >
          <svg
            class="h-5 w-5"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fill-rule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z"
              clip-rule="evenodd"
            />
          </svg>
          Starten
        </button>
        <button
          v-if="campaign?.status === 'active'"
          class="flex items-center gap-2 rounded-lg bg-yellow-600 px-4 py-2 text-sm font-medium text-white hover:bg-yellow-700"
          @click="pauseCampaign"
        >
          <svg
            class="h-5 w-5"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fill-rule="evenodd"
              d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z"
              clip-rule="evenodd"
            />
          </svg>
          Pausieren
        </button>
        <button
          class="flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
          @click="editCampaign"
        >
          <svg
            class="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
            />
          </svg>
          Bearbeiten
        </button>
      </template>
    </PageHeader>

    <div class="sm: lg:">
      <div
        v-if="store.loading"
        class="py-12 text-center text-go4-muted"
      >
        Laden...
      </div>

      <template v-else-if="campaign">
        <!-- Stats Cards -->
        <div class="mb-6 grid gap-4 md:grid-cols-4 lg:grid-cols-7">
          <div
            class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
          >
            <div class="text-sm text-go4-muted">
              Gesamt
            </div>
            <div class="mt-1 text-xl font-bold text-go4-secondary dark:text-white">
              {{ stats.total }}
            </div>
          </div>
          <div
            class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
          >
            <div class="text-sm text-go4-muted">
              Wartend
            </div>
            <div class="mt-1 text-xl font-bold text-gray-600 dark:text-gray-400">
              {{ stats.pending }}
            </div>
          </div>
          <div
            class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
          >
            <div class="text-sm text-go4-muted">
              Aktiv
            </div>
            <div class="mt-1 text-xl font-bold text-blue-600">
              {{ stats.active }}
            </div>
          </div>
          <div
            class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
          >
            <div class="text-sm text-go4-muted">
              Abgeschlossen
            </div>
            <div class="mt-1 text-xl font-bold text-green-600">
              {{ stats.completed }}
            </div>
          </div>
          <div
            class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
          >
            <div class="text-sm text-go4-muted">
              Antworten
            </div>
            <div class="mt-1 text-xl font-bold text-indigo-600">
              {{ stats.replied }}
            </div>
          </div>
          <div
            class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
          >
            <div class="text-sm text-go4-muted">
              Gestoppt
            </div>
            <div class="mt-1 text-xl font-bold text-yellow-600">
              {{ stats.stopped }}
            </div>
          </div>
          <div
            class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
          >
            <div class="text-sm text-go4-muted">
              Fehlgeschlagen
            </div>
            <div class="mt-1 text-xl font-bold text-red-600">
              {{ stats.failed }}
            </div>
          </div>
        </div>

        <!-- Campaign Steps -->
        <div
          class="mb-6 rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
        >
          <h3 class="mb-3 text-sm font-medium text-go4-secondary dark:text-white">
            Workflow ({{ campaign.steps?.length || 0 }} Schritte)
          </h3>
          <div class="flex items-center gap-2 overflow-x-auto pb-2">
            <div
              v-for="(step, index) in campaign.steps"
              :key="step.id"
              class="flex items-center gap-2"
            >
              <div
                class="flex flex-shrink-0 flex-col items-center rounded-lg bg-gray-50 px-3 py-2 dark:bg-gray-700"
              >
                <span class="text-xs text-go4-muted">
                  {{ index + 1 }}
                </span>
                <span
                  class="whitespace-nowrap text-sm font-medium text-go4-secondary dark:text-white"
                >
                  {{ stepTypeLabels[step.action_type] || step.action_type }}
                </span>
                <span
                  v-if="step.delay_hours > 0"
                  class="text-xs text-go4-muted"
                >
                  +{{ step.delay_hours }}h
                </span>
              </div>
              <svg
                v-if="index < campaign.steps.length - 1"
                class="h-4 w-4 flex-shrink-0 text-gray-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </div>
          </div>
        </div>

        <!-- Leads Section -->
        <div
          class="rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800"
        >
          <div
            class="flex items-center justify-between border-b border-gray-200 p-4 dark:border-gray-700"
          >
            <h3 class="text-lg font-medium text-go4-secondary dark:text-white">
              Leads
            </h3>
            <button
              class="flex items-center gap-2 rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark"
              @click="openAddLeads"
            >
              <svg
                class="h-4 w-4"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fill-rule="evenodd"
                  d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
                  clip-rule="evenodd"
                />
              </svg>
              Leads hinzufuegen
            </button>
          </div>

          <div class="border-b border-gray-200 p-4 dark:border-gray-700">
            <div class="flex items-center gap-4">
              <SearchInput
                v-model="searchQuery"
                placeholder="Lead suchen..."
                class="w-64"
              />
              <select
                v-model="statusFilter"
                class="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
              >
                <option value="">
                  Alle Status
                </option>
                <option value="pending">
                  Wartend
                </option>
                <option value="active">
                  Aktiv
                </option>
                <option value="completed">
                  Abgeschlossen
                </option>
                <option value="replied">
                  Antwort erhalten
                </option>
                <option value="stopped">
                  Gestoppt
                </option>
                <option value="failed">
                  Fehlgeschlagen
                </option>
              </select>
              <span class="ml-auto text-sm text-go4-muted"> {{ filteredLeads.length }} Leads </span>
            </div>
          </div>

          <EmptyState
            v-if="filteredLeads.length === 0"
            title="Keine Leads"
            class="py-8"
          >
            <button
              class="mt-4 rounded-lg bg-go4-primary px-4 py-2 text-sm text-white hover:bg-go4-primary-dark"
              @click="openAddLeads"
            >
              Leads hinzufuegen
            </button>
          </EmptyState>

          <div
            v-else
            class="divide-y divide-gray-200 dark:divide-gray-700"
          >
            <div
              v-for="lead in filteredLeads"
              :key="lead.id"
              class="flex items-center justify-between p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50"
            >
              <div
                class="flex cursor-pointer items-center gap-4"
                @click="openContact(lead)"
              >
                <div
                  class="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-gray-200 text-sm font-medium text-gray-600 dark:bg-gray-700 dark:text-gray-300"
                >
                  {{ lead.contact_name?.charAt(0) || '?' }}
                </div>
                <div>
                  <div class="font-medium text-go4-secondary dark:text-white">
                    {{ lead.contact_name }}
                  </div>
                  <div class="text-sm text-go4-muted dark:text-gray-400">
                    {{ lead.contact_company || 'Kein Unternehmen' }}
                  </div>
                </div>
              </div>

              <div class="flex items-center gap-4">
                <div class="text-right">
                  <span
                    :class="statusColors[lead.status]"
                    class="rounded-full px-2 py-0.5 text-xs font-medium"
                  >
                    {{ statusLabels[lead.status] }}
                  </span>
                  <div
                    v-if="lead.current_step"
                    class="mt-1 text-xs text-go4-muted"
                  >
                    Schritt {{ lead.current_step }} / {{ campaign.steps?.length || 0 }}
                  </div>
                </div>

                <div class="flex gap-1">
                  <button
                    v-if="lead.status === 'active'"
                    class="rounded p-1 text-gray-400 hover:bg-yellow-100 hover:text-yellow-600"
                    title="Stoppen"
                    @click.stop="stopLead(lead)"
                  >
                    <svg
                      class="h-4 w-4"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fill-rule="evenodd"
                        d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z"
                        clip-rule="evenodd"
                      />
                    </svg>
                  </button>
                  <button
                    class="rounded p-1 text-gray-400 hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-900/30"
                    title="Entfernen"
                    @click.stop="confirmRemoveLead(lead)"
                  >
                    <svg
                      class="h-4 w-4"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                      />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- Add Leads Modal -->
    <div
      v-if="showAddLeadsModal"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      @click.self="showAddLeadsModal = false"
    >
      <div
        class="mx-4 max-h-[80vh] w-full max-w-2xl overflow-hidden rounded-lg bg-white shadow-xl dark:bg-gray-800"
      >
        <div
          class="flex items-center justify-between border-b border-gray-200 p-4 dark:border-gray-700"
        >
          <h3 class="text-lg font-medium text-go4-secondary dark:text-white">
            Leads hinzufuegen
          </h3>
          <button
            class="text-gray-400 hover:text-gray-600"
            @click="showAddLeadsModal = false"
          >
            <svg
              class="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <div class="max-h-96 overflow-y-auto p-4">
          <EmptyState
            v-if="availableContacts.length === 0"
            title="Keine verfuegbaren Kontakte"
          />

          <div
            v-else
            class="space-y-2"
          >
            <label
              v-for="contact in availableContacts"
              :key="contact.id"
              class="flex cursor-pointer items-center gap-3 rounded-lg border border-gray-200 p-3 hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-700"
              :class="{
                'border-go4-primary bg-go4-primary/5': selectedContacts.includes(contact.id)
              }"
            >
              <input
                type="checkbox"
                :checked="selectedContacts.includes(contact.id)"
                class="h-4 w-4 rounded border-gray-300 text-go4-primary focus:ring-go4-primary"
                @change="toggleContact(contact.id)"
              >
              <div class="flex-1">
                <div class="font-medium text-go4-secondary dark:text-white">
                  {{ contact.name }}
                </div>
                <div class="text-sm text-go4-muted dark:text-gray-400">
                  {{ contact.company_name || contact.headline || 'Kein Unternehmen' }}
                </div>
              </div>
            </label>
          </div>
        </div>

        <div
          class="flex items-center justify-between border-t border-gray-200 p-4 dark:border-gray-700"
        >
          <span class="text-sm text-go4-muted"> {{ selectedContacts.length }} ausgewaehlt </span>
          <div class="flex gap-3">
            <button
              class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
              @click="showAddLeadsModal = false"
            >
              Abbrechen
            </button>
            <button
              class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark disabled:opacity-50"
              :disabled="selectedContacts.length === 0 || addingLeads"
              @click="addSelectedLeads"
            >
              {{ addingLeads ? 'Hinzufuegen...' : `${selectedContacts.length} Leads hinzufuegen` }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Remove Lead Confirmation -->
    <ConfirmDialog
      :open="showRemoveLeadConfirm"
      title="Lead entfernen?"
      :message="`Moechtest du '${leadToRemove?.contact_name}' aus dieser Kampagne entfernen?`"
      confirm-text="Entfernen"
      variant="danger"
      @confirm="removeLead"
      @cancel="showRemoveLeadConfirm = false"
    />
  </div>
</template>
