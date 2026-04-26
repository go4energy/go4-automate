<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useFunnelsStore } from '@/stores/funnels'
import PageHeader from '@/components/ui/PageHeader.vue'
import AvatarInitials from '@/components/ui/AvatarInitials.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import HandoffStatus from '@/components/funnels/HandoffStatus.vue'

const route = useRoute()
const router = useRouter()
const store = useFunnelsStore()

const prospectId = computed(() => Number(route.params.id))

// Modals
const showEditModal = ref(false)
const showActivityModal = ref(false)
const showHandoffConfirm = ref(false)
const showDeleteConfirm = ref(false)

// Form data
const prospectForm = ref({
  name: '',
  email: '',
  phone: '',
  mobile: '',
  position: '',
  department: '',
  linkedin_url: '',
  status: 'new',
  score: 0,
  tags: []
})
const activityForm = ref({
  activity_type: 'email_sent',
  subject: '',
  content: '',
  channel: ''
})
const formLoading = ref(false)

const activityTypes = [
  { value: 'email_sent', label: 'E-Mail gesendet' },
  { value: 'email_opened', label: 'E-Mail geoeffnet' },
  { value: 'email_replied', label: 'E-Mail beantwortet' },
  { value: 'linkedin_connection_sent', label: 'LinkedIn Anfrage gesendet' },
  { value: 'linkedin_accepted', label: 'LinkedIn akzeptiert' },
  { value: 'linkedin_message_sent', label: 'LinkedIn Nachricht gesendet' },
  { value: 'call_made', label: 'Anruf geführt' },
  { value: 'call_answered', label: 'Anruf beantwortet' },
  { value: 'voicemail_left', label: 'Voicemail hinterlassen' },
  { value: 'meeting_scheduled', label: 'Meeting geplant' },
  { value: 'note', label: 'Notiz' }
]

const prospect = computed(() => store.currentProspect)
const activities = computed(() => store.activities)
const handoffs = computed(() => store.handoffs.filter((h) => h.prospect_id === prospectId.value))

onMounted(async () => {
  await loadProspect()
})

watch(prospectId, async () => {
  await loadProspect()
})

async function loadProspect() {
  await store.fetchProspect(prospectId.value)
  await store.fetchActivities(prospectId.value)
  // Load handoffs for this prospect
  if (prospect.value?.funnel_id) {
    await store.fetchHandoffs(prospect.value.funnel_id)
  }
}

function goBack() {
  if (prospect.value?.funnel_id) {
    router.push(`/funnels/${prospect.value.funnel_id}`)
  } else {
    router.push('/funnels')
  }
}

function openEditModal() {
  if (!prospect.value) return
  prospectForm.value = {
    name: prospect.value.name || '',
    email: prospect.value.email || '',
    phone: prospect.value.phone || '',
    mobile: prospect.value.mobile || '',
    position: prospect.value.position || '',
    department: prospect.value.department || '',
    linkedin_url: prospect.value.linkedin_url || '',
    status: prospect.value.status || 'new',
    score: prospect.value.score || 0,
    tags: prospect.value.tags || []
  }
  showEditModal.value = true
}

function openActivityModal() {
  activityForm.value = {
    activity_type: 'email_sent',
    subject: '',
    content: '',
    channel: ''
  }
  showActivityModal.value = true
}

async function updateProspect() {
  if (!prospectForm.value.name.trim()) return

  formLoading.value = true
  try {
    await store.editProspect(prospectId.value, prospectForm.value)
    showEditModal.value = false
  } finally {
    formLoading.value = false
  }
}

async function logActivity() {
  if (!activityForm.value.activity_type) return

  formLoading.value = true
  try {
    await store.logActivity(prospectId.value, activityForm.value)
    showActivityModal.value = false
    await store.fetchActivities(prospectId.value)
  } finally {
    formLoading.value = false
  }
}

async function triggerHandoff() {
  formLoading.value = true
  try {
    await store.triggerHandoff(prospectId.value)
    showHandoffConfirm.value = false
    await loadProspect()
  } finally {
    formLoading.value = false
  }
}

async function deleteProspect() {
  if (!prospect.value) return

  try {
    await store.removeProspect(prospectId.value)
    router.push(`/funnels/${prospect.value.funnel_id}`)
  } catch {
    // Error is in store
  }
}

async function retryHandoff(handoff) {
  await store.retryHandoff(handoff.id)
  await loadProspect()
}

function getStatusColor(status) {
  const colors = {
    new: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
    contacted: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    engaged: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
    qualified: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    handed_off: 'bg-teal-100 text-teal-800 dark:bg-teal-900 dark:text-teal-200',
    do_not_contact: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
  }
  return colors[status] || colors.new
}

function getStatusLabel(status) {
  const labels = {
    new: 'Neu',
    contacted: 'Kontaktiert',
    engaged: 'Interessiert',
    qualified: 'Qualifiziert',
    handed_off: 'Uebergeben',
    do_not_contact: 'Nicht kontaktieren'
  }
  return labels[status] || status
}

function getActivityIcon(type) {
  const icons = {
    email_sent:
      'M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z',
    email_opened:
      'M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z',
    email_replied:
      'M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z',
    linkedin_connection_sent:
      'M16 8a6 6 0 016 6v7h-4v-7a2 2 0 00-2-2 2 2 0 00-2 2v7h-4v-7a6 6 0 016-6z M2 9h4v12H2z M4 6a2 2 0 100-4 2 2 0 000 4z',
    linkedin_accepted:
      'M16 8a6 6 0 016 6v7h-4v-7a2 2 0 00-2-2 2 2 0 00-2 2v7h-4v-7a6 6 0 016-6z M2 9h4v12H2z M4 6a2 2 0 100-4 2 2 0 000 4z',
    linkedin_message_sent:
      'M16 8a6 6 0 016 6v7h-4v-7a2 2 0 00-2-2 2 2 0 00-2 2v7h-4v-7a6 6 0 016-6z M2 9h4v12H2z M4 6a2 2 0 100-4 2 2 0 000 4z',
    call_made:
      'M2 3a1 1 0 011-1h2.153a1 1 0 01.986.836l.74 4.435a1 1 0 01-.54 1.06l-1.548.773a11.037 11.037 0 006.105 6.105l.774-1.548a1 1 0 011.059-.54l4.435.74a1 1 0 01.836.986V17a1 1 0 01-1 1h-2C7.82 18 2 12.18 2 5V3z',
    call_answered:
      'M2 3a1 1 0 011-1h2.153a1 1 0 01.986.836l.74 4.435a1 1 0 01-.54 1.06l-1.548.773a11.037 11.037 0 006.105 6.105l.774-1.548a1 1 0 011.059-.54l4.435.74a1 1 0 01.836.986V17a1 1 0 01-1 1h-2C7.82 18 2 12.18 2 5V3z',
    voicemail_left:
      'M2 3a1 1 0 011-1h2.153a1 1 0 01.986.836l.74 4.435a1 1 0 01-.54 1.06l-1.548.773a11.037 11.037 0 006.105 6.105l.774-1.548a1 1 0 011.059-.54l4.435.74a1 1 0 01.836.986V17a1 1 0 01-1 1h-2C7.82 18 2 12.18 2 5V3z',
    meeting_scheduled:
      'M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z',
    stage_changed:
      'M10.293 5.293a1 1 0 011.414 0l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414-1.414L12.586 11H5a1 1 0 110-2h7.586l-2.293-2.293a1 1 0 010-1.414z',
    note: 'M9 2a1 1 0 000 2h2a1 1 0 100-2H9z M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z'
  }
  return icons[type] || icons.note
}

function getActivityLabel(type) {
  const found = activityTypes.find((t) => t.value === type)
  return found?.label || type
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
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
    <template v-else-if="prospect">
      <PageHeader
        :title="prospect.name"
        :subtitle="prospect.position || 'Prospect'"
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
            v-if="prospect.status !== 'handed_off'"
            class="flex items-center gap-2 rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700"
            @click="showHandoffConfirm = true"
          >
            <svg
              class="h-5 w-5"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z"
              />
              <path
                d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z"
              />
            </svg>
            Handoff zu CRM
          </button>
        </template>
      </PageHeader>

      <div class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <div class="grid gap-6 lg:grid-cols-3">
          <!-- Main Content -->
          <div class="lg:col-span-2 space-y-6">
            <!-- Info Card -->
            <div class="rounded-lg bg-white dark:bg-gray-800 p-6 shadow-sm">
              <div class="flex items-start justify-between">
                <div class="flex items-center gap-4">
                  <AvatarInitials
                    :name="prospect.name"
                    size="lg"
                  />
                  <div>
                    <h2 class="text-xl font-semibold text-go4-secondary dark:text-white">
                      {{ prospect.name }}
                    </h2>
                    <p
                      v-if="prospect.position"
                      class="text-go4-muted dark:text-gray-400"
                    >
                      {{ prospect.position }}
                      {{ prospect.company_name ? `@ ${prospect.company_name}` : '' }}
                    </p>
                    <div class="mt-2 flex items-center gap-2">
                      <span
                        class="rounded-full px-2.5 py-0.5 text-xs font-medium"
                        :class="getStatusColor(prospect.status)"
                      >
                        {{ getStatusLabel(prospect.status) }}
                      </span>
                      <span
                        v-if="prospect.is_duplicate"
                        class="rounded-full bg-yellow-100 px-2.5 py-0.5 text-xs font-medium text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200"
                      >
                        Duplikat
                      </span>
                    </div>
                  </div>
                </div>
                <button
                  class="rounded p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700"
                  @click="openEditModal"
                >
                  <svg
                    class="h-5 w-5"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      d="M17.414 2.586a2 2 0 00-2.828 0L7 10.172V13h2.828l7.586-7.586a2 2 0 000-2.828z"
                    />
                  </svg>
                </button>
              </div>

              <!-- Contact Details -->
              <dl class="mt-6 grid gap-4 sm:grid-cols-2">
                <div v-if="prospect.email">
                  <dt class="text-sm text-go4-muted dark:text-gray-400">
                    E-Mail
                  </dt>
                  <dd>
                    <a
                      :href="`mailto:${prospect.email}`"
                      class="text-go4-primary hover:underline"
                    >
                      {{ prospect.email }}
                    </a>
                  </dd>
                </div>
                <div v-if="prospect.phone">
                  <dt class="text-sm text-go4-muted dark:text-gray-400">
                    Telefon
                  </dt>
                  <dd>
                    <a
                      :href="`tel:${prospect.phone}`"
                      class="text-go4-primary hover:underline"
                    >
                      {{ prospect.phone }}
                    </a>
                  </dd>
                </div>
                <div v-if="prospect.mobile">
                  <dt class="text-sm text-go4-muted dark:text-gray-400">
                    Mobil
                  </dt>
                  <dd>
                    <a
                      :href="`tel:${prospect.mobile}`"
                      class="text-go4-primary hover:underline"
                    >
                      {{ prospect.mobile }}
                    </a>
                  </dd>
                </div>
                <div v-if="prospect.linkedin_url">
                  <dt class="text-sm text-go4-muted dark:text-gray-400">
                    LinkedIn
                  </dt>
                  <dd>
                    <a
                      :href="prospect.linkedin_url"
                      target="_blank"
                      class="text-go4-primary hover:underline"
                    >
                      Profil ansehen
                    </a>
                  </dd>
                </div>
                <div v-if="prospect.department">
                  <dt class="text-sm text-go4-muted dark:text-gray-400">
                    Abteilung
                  </dt>
                  <dd class="text-go4-secondary dark:text-white">
                    {{ prospect.department }}
                  </dd>
                </div>
                <div v-if="prospect.seniority">
                  <dt class="text-sm text-go4-muted dark:text-gray-400">
                    Senioritaet
                  </dt>
                  <dd class="text-go4-secondary dark:text-white">
                    {{ prospect.seniority }}
                  </dd>
                </div>
              </dl>

              <!-- Tags -->
              <div
                v-if="prospect.tags?.length"
                class="mt-4"
              >
                <dt class="mb-2 text-sm text-go4-muted dark:text-gray-400">
                  Tags
                </dt>
                <div class="flex flex-wrap gap-1">
                  <span
                    v-for="tag in prospect.tags"
                    :key="tag"
                    class="inline-flex items-center rounded-full bg-gray-100 dark:bg-gray-700 px-2.5 py-0.5 text-xs text-gray-600 dark:text-gray-300"
                  >
                    {{ tag }}
                  </span>
                </div>
              </div>
            </div>

            <!-- Activity Timeline -->
            <div class="rounded-lg bg-white dark:bg-gray-800 p-6 shadow-sm">
              <div class="mb-4 flex items-center justify-between">
                <h3 class="text-lg font-semibold text-go4-secondary dark:text-white">
                  Aktivitaeten
                </h3>
                <button
                  class="flex items-center gap-1 text-sm text-go4-primary hover:underline"
                  @click="openActivityModal"
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
                  Hinzufuegen
                </button>
              </div>

              <div
                v-if="activities.length === 0"
                class="py-8 text-center text-go4-muted"
              >
                Noch keine Aktivitaeten
              </div>

              <div
                v-else
                class="relative"
              >
                <!-- Timeline line -->
                <div class="absolute left-4 top-0 h-full w-0.5 bg-gray-200 dark:bg-gray-700" />

                <div class="space-y-4">
                  <div
                    v-for="activity in activities"
                    :key="activity.id"
                    class="relative flex gap-4 pl-10"
                  >
                    <!-- Icon -->
                    <div
                      class="absolute left-0 flex h-8 w-8 items-center justify-center rounded-full bg-gray-100 dark:bg-gray-700"
                    >
                      <svg
                        class="h-4 w-4 text-gray-600 dark:text-gray-400"
                        viewBox="0 0 20 20"
                        fill="currentColor"
                      >
                        <path :d="getActivityIcon(activity.activity_type)" />
                      </svg>
                    </div>

                    <!-- Content -->
                    <div class="flex-1 pb-4">
                      <div class="flex items-center justify-between">
                        <span class="font-medium text-go4-secondary dark:text-white">
                          {{ getActivityLabel(activity.activity_type) }}
                        </span>
                        <span class="text-xs text-go4-muted dark:text-gray-400">
                          {{ formatDate(activity.activity_date || activity.created_at) }}
                        </span>
                      </div>
                      <p
                        v-if="activity.subject"
                        class="mt-1 text-sm text-go4-secondary dark:text-gray-200"
                      >
                        {{ activity.subject }}
                      </p>
                      <p
                        v-if="activity.content"
                        class="mt-1 text-sm text-go4-muted dark:text-gray-400"
                      >
                        {{ activity.content }}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Handoff History -->
            <div
              v-if="handoffs.length > 0"
              class="rounded-lg bg-white dark:bg-gray-800 p-6 shadow-sm"
            >
              <h3 class="mb-4 text-lg font-semibold text-go4-secondary dark:text-white">
                Handoff Historie
              </h3>
              <div class="space-y-3">
                <HandoffStatus
                  v-for="handoff in handoffs"
                  :key="handoff.id"
                  :handoff="handoff"
                  @retry="retryHandoff"
                />
              </div>
            </div>
          </div>

          <!-- Sidebar -->
          <div class="space-y-6">
            <!-- Score Card -->
            <div class="rounded-lg bg-white dark:bg-gray-800 p-6 shadow-sm">
              <h3 class="mb-4 text-lg font-semibold text-go4-secondary dark:text-white">
                Score
              </h3>
              <div class="flex items-center justify-center">
                <div
                  class="flex h-24 w-24 items-center justify-center rounded-full border-4"
                  :class="{
                    'border-green-500 text-green-600': prospect.score >= 70,
                    'border-yellow-500 text-yellow-600':
                      prospect.score >= 40 && prospect.score < 70,
                    'border-gray-300 text-gray-500 dark:border-gray-600 dark:text-gray-400':
                      prospect.score < 40
                  }"
                >
                  <span class="text-3xl font-bold">{{ prospect.score || 0 }}</span>
                </div>
              </div>
              <p class="mt-4 text-center text-sm text-go4-muted dark:text-gray-400">
                {{
                  prospect.score >= 70
                    ? 'Hoch qualifiziert'
                    : prospect.score >= 40
                      ? 'Mittel'
                      : 'Niedrig'
                }}
              </p>
            </div>

            <!-- CRM Links -->
            <div
              v-if="prospect.crm_contact_id || prospect.crm_deal_id"
              class="rounded-lg bg-white dark:bg-gray-800 p-6 shadow-sm"
            >
              <h3 class="mb-4 text-lg font-semibold text-go4-secondary dark:text-white">
                CRM Verknuepfungen
              </h3>
              <div class="space-y-2">
                <router-link
                  v-if="prospect.crm_contact_id"
                  :to="`/contacts/${prospect.crm_contact_id}`"
                  class="flex items-center gap-2 text-go4-primary hover:underline"
                >
                  <svg
                    class="h-4 w-4"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fill-rule="evenodd"
                      d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"
                      clip-rule="evenodd"
                    />
                  </svg>
                  CRM Kontakt #{{ prospect.crm_contact_id }}
                </router-link>
                <router-link
                  v-if="prospect.crm_deal_id"
                  :to="`/crm/deals/${prospect.crm_deal_id}`"
                  class="flex items-center gap-2 text-go4-primary hover:underline"
                >
                  <svg
                    class="h-4 w-4"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fill-rule="evenodd"
                      d="M4 4a2 2 0 00-2 2v4a2 2 0 002 2V6h10a2 2 0 00-2-2H4zm2 6a2 2 0 012-2h8a2 2 0 012 2v4a2 2 0 01-2 2H8a2 2 0 01-2-2v-4zm6 4a2 2 0 100-4 2 2 0 000 4z"
                      clip-rule="evenodd"
                    />
                  </svg>
                  CRM Deal #{{ prospect.crm_deal_id }}
                </router-link>
              </div>
            </div>

            <!-- Meta Info -->
            <div class="rounded-lg bg-white dark:bg-gray-800 p-6 shadow-sm">
              <h3 class="mb-4 text-lg font-semibold text-go4-secondary dark:text-white">
                Details
              </h3>
              <dl class="space-y-3 text-sm">
                <div>
                  <dt class="text-go4-muted dark:text-gray-400">
                    Quelle
                  </dt>
                  <dd class="text-go4-secondary dark:text-white">
                    {{ prospect.source || '-' }}
                  </dd>
                </div>
                <div v-if="prospect.stage_name">
                  <dt class="text-go4-muted dark:text-gray-400">
                    Stage
                  </dt>
                  <dd class="text-go4-secondary dark:text-white">
                    {{ prospect.stage_name }}
                  </dd>
                </div>
                <div>
                  <dt class="text-go4-muted dark:text-gray-400">
                    E-Mail verifiziert
                  </dt>
                  <dd class="text-go4-secondary dark:text-white">
                    {{ prospect.email_verified ? 'Ja' : 'Nein' }}
                  </dd>
                </div>
                <div>
                  <dt class="text-go4-muted dark:text-gray-400">
                    Erstellt
                  </dt>
                  <dd class="text-go4-secondary dark:text-white">
                    {{ formatDate(prospect.created_at) }}
                  </dd>
                </div>
                <div>
                  <dt class="text-go4-muted dark:text-gray-400">
                    Aktualisiert
                  </dt>
                  <dd class="text-go4-secondary dark:text-white">
                    {{ formatDate(prospect.updated_at) }}
                  </dd>
                </div>
              </dl>
            </div>

            <!-- Danger Zone -->
            <div
              class="rounded-lg border border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20 p-4"
            >
              <button
                class="w-full rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
                @click="showDeleteConfirm = true"
              >
                Prospect loeschen
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- Edit Modal -->
    <Teleport to="body">
      <div
        v-if="showEditModal"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
        @click.self="showEditModal = false"
      >
        <div
          class="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-lg bg-white dark:bg-gray-800 p-6 shadow-xl"
        >
          <h2 class="mb-4 text-lg font-semibold text-go4-secondary dark:text-white">
            Prospect bearbeiten
          </h2>

          <form
            class="space-y-4"
            @submit.prevent="updateProspect"
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
                  E-Mail
                </label>
                <input
                  v-model="prospectForm.email"
                  type="email"
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
                  Mobil
                </label>
                <input
                  v-model="prospectForm.mobile"
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
                  Abteilung
                </label>
                <input
                  v-model="prospectForm.department"
                  type="text"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                >
              </div>
              <div class="sm:col-span-2">
                <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                  LinkedIn URL
                </label>
                <input
                  v-model="prospectForm.linkedin_url"
                  type="url"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                >
              </div>
              <div>
                <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                  Status
                </label>
                <select
                  v-model="prospectForm.status"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                >
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
                  <option value="do_not_contact">
                    Nicht kontaktieren
                  </option>
                </select>
              </div>
              <div>
                <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                  Score (0-100)
                </label>
                <input
                  v-model.number="prospectForm.score"
                  type="number"
                  min="0"
                  max="100"
                  class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                >
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
                :disabled="formLoading || !prospectForm.name.trim()"
              >
                {{ formLoading ? 'Speichern...' : 'Speichern' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Activity Modal -->
    <Teleport to="body">
      <div
        v-if="showActivityModal"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
        @click.self="showActivityModal = false"
      >
        <div class="w-full max-w-md rounded-lg bg-white dark:bg-gray-800 p-6 shadow-xl">
          <h2 class="mb-4 text-lg font-semibold text-go4-secondary dark:text-white">
            Aktivitaet hinzufuegen
          </h2>

          <form
            class="space-y-4"
            @submit.prevent="logActivity"
          >
            <div>
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                Typ *
              </label>
              <select
                v-model="activityForm.activity_type"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
                <option
                  v-for="type in activityTypes"
                  :key="type.value"
                  :value="type.value"
                >
                  {{ type.label }}
                </option>
              </select>
            </div>

            <div>
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                Betreff
              </label>
              <input
                v-model="activityForm.subject"
                type="text"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
            </div>

            <div>
              <label class="mb-1 block text-sm font-medium text-go4-secondary dark:text-gray-200">
                Notiz
              </label>
              <textarea
                v-model="activityForm.content"
                rows="3"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              />
            </div>

            <div class="flex justify-end gap-3 pt-4">
              <button
                type="button"
                class="rounded-lg px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
                @click="showActivityModal = false"
              >
                Abbrechen
              </button>
              <button
                type="submit"
                class="rounded-lg bg-go4-primary px-4 py-2 text-sm text-white hover:bg-go4-primary-dark disabled:opacity-50"
                :disabled="formLoading"
              >
                {{ formLoading ? 'Speichern...' : 'Speichern' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Handoff Confirmation -->
    <ConfirmDialog
      :open="showHandoffConfirm"
      title="Handoff zu CRM?"
      message="Der Prospect wird ins CRM uebertragen. Ein Kontakt und optional ein Deal werden erstellt."
      confirm-text="Handoff starten"
      @confirm="triggerHandoff"
      @cancel="showHandoffConfirm = false"
    />

    <!-- Delete Confirmation -->
    <ConfirmDialog
      :open="showDeleteConfirm"
      title="Prospect loeschen?"
      :message="`Möchtest du '${prospect?.name}' wirklich löschen? Alle Aktivitäten werden ebenfalls gelöscht.`"
      confirm-text="Loeschen"
      variant="danger"
      @confirm="deleteProspect"
      @cancel="showDeleteConfirm = false"
    />
  </div>
</template>
