<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useLinkedInStore } from '@/stores/linkedin'
import PageHeader from '@/components/ui/PageHeader.vue'
import ProfileCard from '@/components/linkedin/ProfileCard.vue'

const router = useRouter()
const route = useRoute()
const store = useLinkedInStore()

const contactId = computed(() => parseInt(route.params.id))
const contact = computed(() => store.currentContact)

// Merge contact DB fields + raw_data into a single profile object for ProfileCard
const profileData = computed(() => {
  const c = contact.value
  if (!c) return null
  const raw = c.raw_data || {}
  return {
    name: c.name,
    headline: c.headline,
    location: c.location,
    company_name: c.company_name,
    position: c.position,
    summary: c.summary,
    linkedin_url: c.linkedin_url,
    profile_picture_url: c.profile_picture_url,
    follower_count: c.follower_count,
    connection_count: c.connection_count,
    is_premium: c.is_premium,
    connection_status: raw.connection_status,
    experience: c.experience?.length ? c.experience : raw.experience || [],
    education: c.education?.length ? c.education : raw.education || [],
    skills: c.skills?.length ? c.skills : raw.skills || [],
    languages: c.languages?.length ? c.languages : raw.languages || [],
    certifications: raw.certifications || [],
    contact_info: raw.contact_info || null,
    interests: c.interests || raw.interests || null,
    hashtags: raw.hashtags || [],
  }
})

const statusColors = {
  scraped: 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300',
  imported: 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300',
  skipped: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
  failed: 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300'
}

const statusLabels = {
  scraped: 'Gescraped',
  imported: 'Importiert',
  skipped: 'Uebersprungen',
  failed: 'Fehlgeschlagen'
}

const excludeLoading = ref(false)

onMounted(async () => {
  await store.fetchContact(contactId.value)
})

async function handleToggleExclude() {
  excludeLoading.value = true
  try {
    await store.toggleExclude(contactId.value)
  } finally {
    excludeLoading.value = false
  }
}

function goBack() {
  router.push({ name: 'linkedin', query: { tab: 'contacts' } })
}

function formatDate(dateString) {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleDateString('de-DE', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function openLinkedIn() {
  if (contact.value?.linkedin_url) {
    window.open(contact.value.linkedin_url, '_blank')
  }
}

function openSalesNavigator() {
  if (contact.value?.sales_navigator_url) {
    window.open(contact.value.sales_navigator_url, '_blank')
  }
}

function openCompanyLinkedIn() {
  if (contact.value?.company_linkedin_url) {
    window.open(contact.value.company_linkedin_url, '_blank')
  }
}

function sendEmail() {
  if (contact.value?.email) {
    window.location.href = `mailto:${contact.value.email}`
  }
}

function callPhone() {
  if (contact.value?.phone) {
    window.location.href = `tel:${contact.value.phone}`
  }
}

function openWebsite() {
  if (contact.value?.website) {
    const url = contact.value.website.startsWith('http')
      ? contact.value.website
      : `https://${contact.value.website}`
    window.open(url, '_blank')
  }
}

function openTwitter() {
  if (contact.value?.twitter_url) {
    window.open(contact.value.twitter_url, '_blank')
  }
}
</script>

<template>
  <div class="min-h-screen bg-go4-bg dark:bg-gray-900">
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
      class="m-6 rounded-lg bg-red-50 p-4 text-red-700 dark:bg-red-900/20 dark:text-red-400"
    >
      {{ store.error }}
      <button
        type="button"
        class="ml-4 underline"
        @click="goBack"
      >
        Zurueck
      </button>
    </div>

    <!-- Content -->
    <template v-else-if="contact">
      <PageHeader
        :title="contact.name"
        :subtitle="contact.headline || contact.position"
      >
        <template #actions>
          <button
            class="flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
            @click="goBack"
          >
            <svg
              class="h-5 w-5"
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
            Zurueck
          </button>
          <button
            :class="contact.excluded
              ? 'border-red-300 bg-red-50 text-red-700 hover:bg-red-100 dark:border-red-700 dark:bg-red-900/30 dark:text-red-400'
              : 'border-green-300 bg-green-50 text-green-700 hover:bg-green-100 dark:border-green-700 dark:bg-green-900/30 dark:text-green-400'"
            class="flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium"
            :disabled="excludeLoading"
            @click="handleToggleExclude"
          >
            {{ contact.excluded ? 'Deaktiviert' : 'Aktiv' }}
          </button>
          <button
            v-if="contact.linkedin_url"
            class="flex items-center gap-2 rounded-lg bg-[#0A66C2] px-4 py-2 text-sm font-medium text-white hover:bg-[#004182]"
            @click="openLinkedIn"
          >
            <svg
              class="h-5 w-5"
              viewBox="0 0 24 24"
              fill="currentColor"
            >
              <path
                d="M4 3a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2V5a2 2 0 00-2-2H4zm3 5a1.5 1.5 0 100-3 1.5 1.5 0 000 3zm-1.5 2h3v9h-3v-9zm5.5 0h3v1.5s1-1.5 3-1.5c1.5 0 3 1 3 4v5h-3v-4c0-1.5-.5-2-1.5-2s-1.5 1-1.5 2v4h-3v-9z"
              />
            </svg>
            LinkedIn Profil
          </button>
        </template>
      </PageHeader>

      <!-- Excluded Warning -->
      <div
        v-if="contact.excluded"
        class="mx-auto max-w-5xl px-4 pt-4 sm:px-6 lg:px-8"
      >
        <div class="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
          Dieser Kontakt ist <strong>deaktiviert</strong> und wird nicht fuer Messaging oder Pipelines verwendet.
        </div>
      </div>

      <div class="mx-auto max-w-5xl px-4 py-6 sm:px-6 lg:px-8">
        <div class="grid gap-6 lg:grid-cols-3">
          <!-- Left Column: Main Info -->
          <div class="space-y-6 lg:col-span-2">
            <!-- Status Badge -->
            <div class="flex items-center gap-2">
              <span
                v-if="contact.contact_degree"
                class="rounded bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600 dark:bg-gray-700 dark:text-gray-300"
              >
                {{ contact.contact_degree }}. Grad
              </span>
              <span
                :class="statusColors[contact.status]"
                class="rounded-full px-2 py-0.5 text-xs font-medium"
              >
                {{ statusLabels[contact.status] }}
              </span>
            </div>

            <!-- Profile via shared component -->
            <ProfileCard :profile="profileData" />
          </div>

          <!-- Right Column: Sidebar -->
          <div class="space-y-6">
            <!-- Contact Actions -->
            <div
              class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800"
            >
              <h3 class="text-sm font-medium text-go4-secondary dark:text-white">
                Kontakt
              </h3>
              <div class="mt-4 space-y-3">
                <button
                  v-if="contact.email"
                  class="flex w-full items-center gap-3 rounded-lg border border-gray-200 px-4 py-2 text-sm hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-700"
                  @click="sendEmail"
                >
                  <svg
                    class="h-5 w-5 text-go4-muted"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                    />
                  </svg>
                  <span class="text-go4-secondary dark:text-white">{{ contact.email }}</span>
                </button>

                <button
                  v-if="contact.phone"
                  class="flex w-full items-center gap-3 rounded-lg border border-gray-200 px-4 py-2 text-sm hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-700"
                  @click="callPhone"
                >
                  <svg
                    class="h-5 w-5 text-go4-muted"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"
                    />
                  </svg>
                  <span class="text-go4-secondary dark:text-white">{{ contact.phone }}</span>
                </button>

                <button
                  v-if="contact.website"
                  class="flex w-full items-center gap-3 rounded-lg border border-gray-200 px-4 py-2 text-sm hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-700"
                  @click="openWebsite"
                >
                  <svg
                    class="h-5 w-5 text-go4-muted"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"
                    />
                  </svg>
                  <span class="truncate text-go4-secondary dark:text-white">{{
                    contact.website
                  }}</span>
                </button>

                <button
                  v-if="contact.twitter_url"
                  class="flex w-full items-center gap-3 rounded-lg border border-gray-200 px-4 py-2 text-sm hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-700"
                  @click="openTwitter"
                >
                  <svg
                    class="h-5 w-5 text-go4-muted"
                    fill="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"
                    />
                  </svg>
                  <span class="text-go4-secondary dark:text-white">Twitter/X</span>
                </button>
              </div>
            </div>

            <!-- Pipeline Enrollments -->
            <div
              v-if="contact.pipelines?.length"
              class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800"
            >
              <h3 class="text-sm font-medium text-go4-secondary dark:text-white">
                Pipelines ({{ contact.pipelines.length }})
              </h3>
              <div class="mt-4 space-y-3">
                <div
                  v-for="pipeline in contact.pipelines"
                  :key="pipeline.id"
                  class="flex items-center justify-between rounded-lg border border-gray-100 p-3 dark:border-gray-700"
                >
                  <div>
                    <div class="text-sm font-medium text-go4-secondary dark:text-white">
                      {{ pipeline.name }}
                    </div>
                    <div class="mt-0.5 text-xs text-go4-muted dark:text-gray-400">
                      Stage: {{ pipeline.stage || '-' }}
                    </div>
                  </div>
                  <span
                    :class="{
                      'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300': pipeline.status === 'active',
                      'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-300': pipeline.status === 'paused',
                      'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300': pipeline.status === 'completed' || pipeline.status === 'stopped'
                    }"
                    class="rounded-full px-2 py-0.5 text-xs font-medium"
                  >
                    {{ pipeline.status }}
                  </span>
                </div>
              </div>
            </div>

            <!-- Company -->
            <div
              v-if="contact.company_name"
              class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800"
            >
              <h3 class="text-sm font-medium text-go4-secondary dark:text-white">
                Unternehmen
              </h3>
              <div class="mt-4">
                <div class="font-medium text-go4-secondary dark:text-white">
                  {{ contact.company_name }}
                </div>
                <div
                  v-if="contact.position"
                  class="mt-1 text-sm text-go4-muted dark:text-gray-400"
                >
                  {{ contact.position }}
                </div>
                <div
                  v-if="contact.company_industry || contact.company_size"
                  class="mt-2 text-sm text-go4-muted dark:text-gray-400"
                >
                  <span v-if="contact.company_industry">{{ contact.company_industry }}</span>
                  <span v-if="contact.company_industry && contact.company_size"> - </span>
                  <span v-if="contact.company_size">{{ contact.company_size }}</span>
                </div>
                <button
                  v-if="contact.company_linkedin_url"
                  class="mt-3 flex items-center gap-2 text-sm text-[#0A66C2] hover:underline"
                  @click="openCompanyLinkedIn"
                >
                  <svg
                    class="h-4 w-4"
                    viewBox="0 0 24 24"
                    fill="currentColor"
                  >
                    <path
                      d="M4 3a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2V5a2 2 0 00-2-2H4zm3 5a1.5 1.5 0 100-3 1.5 1.5 0 000 3zm-1.5 2h3v9h-3v-9zm5.5 0h3v1.5s1-1.5 3-1.5c1.5 0 3 1 3 4v5h-3v-4c0-1.5-.5-2-1.5-2s-1.5 1-1.5 2v4h-3v-9z"
                    />
                  </svg>
                  Unternehmensprofil
                </button>
              </div>
            </div>

            <!-- LinkedIn Links -->
            <div
              class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800"
            >
              <h3 class="text-sm font-medium text-go4-secondary dark:text-white">
                LinkedIn
              </h3>
              <div class="mt-4 space-y-3">
                <button
                  v-if="contact.linkedin_url"
                  class="flex w-full items-center gap-3 rounded-lg bg-[#0A66C2] px-4 py-2 text-sm text-white hover:bg-[#004182]"
                  @click="openLinkedIn"
                >
                  <svg
                    class="h-5 w-5"
                    viewBox="0 0 24 24"
                    fill="currentColor"
                  >
                    <path
                      d="M4 3a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2V5a2 2 0 00-2-2H4zm3 5a1.5 1.5 0 100-3 1.5 1.5 0 000 3zm-1.5 2h3v9h-3v-9zm5.5 0h3v1.5s1-1.5 3-1.5c1.5 0 3 1 3 4v5h-3v-4c0-1.5-.5-2-1.5-2s-1.5 1-1.5 2v4h-3v-9z"
                    />
                  </svg>
                  Profil oeffnen
                </button>
                <button
                  v-if="contact.sales_navigator_url"
                  class="flex w-full items-center gap-3 rounded-lg border border-[#0A66C2] px-4 py-2 text-sm text-[#0A66C2] hover:bg-blue-50 dark:hover:bg-blue-900/20"
                  @click="openSalesNavigator"
                >
                  <svg
                    class="h-5 w-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                    />
                  </svg>
                  Sales Navigator
                </button>
              </div>
            </div>

            <!-- Meta Info -->
            <div
              class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800"
            >
              <h3 class="text-sm font-medium text-go4-secondary dark:text-white">
                Details
              </h3>
              <dl class="mt-4 space-y-3 text-sm">
                <div v-if="contact.linkedin_id">
                  <dt class="text-go4-muted dark:text-gray-500">
                    LinkedIn ID
                  </dt>
                  <dd class="mt-1 text-go4-secondary dark:text-white">
                    {{ contact.linkedin_id }}
                  </dd>
                </div>
                <div v-if="contact.gender">
                  <dt class="text-go4-muted dark:text-gray-500">
                    Geschlecht
                  </dt>
                  <dd class="mt-1 text-go4-secondary dark:text-white">
                    {{ contact.gender }}
                  </dd>
                </div>
                <div>
                  <dt class="text-go4-muted dark:text-gray-500">
                    Gescraped am
                  </dt>
                  <dd class="mt-1 text-go4-secondary dark:text-white">
                    {{ formatDate(contact.created_at) }}
                  </dd>
                </div>
                <div v-if="contact.imported_at">
                  <dt class="text-go4-muted dark:text-gray-500">
                    Importiert am
                  </dt>
                  <dd class="mt-1 text-go4-secondary dark:text-white">
                    {{ formatDate(contact.imported_at) }}
                  </dd>
                </div>
                <div v-if="contact.funnel_prospect_id">
                  <dt class="text-go4-muted dark:text-gray-500">
                    Funnel Prospect ID
                  </dt>
                  <dd class="mt-1 text-go4-secondary dark:text-white">
                    {{ contact.funnel_prospect_id }}
                  </dd>
                </div>
                <div v-if="contact.scrape_error">
                  <dt class="text-go4-muted dark:text-gray-500">
                    Fehler
                  </dt>
                  <dd class="mt-1 text-red-600 dark:text-red-400">
                    {{ contact.scrape_error }}
                  </dd>
                </div>
              </dl>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
