<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useContactsStore } from '@/stores/contacts'
import PageHeader from '@/components/ui/PageHeader.vue'
import AvatarInitials from '@/components/ui/AvatarInitials.vue'
import ContactFormModal from '@/components/contacts/ContactFormModal.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import ActivityTimeline from '@/components/engagement/ActivityTimeline.vue'

const router = useRouter()
const route = useRoute()
const store = useContactsStore()

const contactId = computed(() => parseInt(route.params.id))

// Modal state
const showEditModal = ref(false)
const showDeleteDialog = ref(false)
const modalLoading = ref(false)
const deleteLoading = ref(false)

const contact = computed(() => store.currentContact)

onMounted(async () => {
  await store.fetchContact(contactId.value)
  await store.fetchCompanies()
})

function goBack() {
  router.push({ name: 'contacts' })
}

function openEditModal() {
  showEditModal.value = true
}

async function saveContact(data) {
  modalLoading.value = true
  try {
    await store.editContact(contactId.value, data)
    showEditModal.value = false
  } catch {
    // Error is set in store
  } finally {
    modalLoading.value = false
  }
}

async function deleteContact() {
  deleteLoading.value = true
  try {
    await store.removeContact(contactId.value)
    router.push({ name: 'contacts' })
  } catch {
    // Error is set in store
  } finally {
    deleteLoading.value = false
  }
}

function emailContact() {
  if (contact.value?.email) {
    window.location.href = `mailto:${contact.value.email}`
  }
}

function callContact() {
  if (contact.value?.phone) {
    window.location.href = `tel:${contact.value.phone}`
  }
}

function goToCompany() {
  if (contact.value?.company_id) {
    router.push({ name: 'company-detail', params: { id: contact.value.company_id } })
  }
}

function formatDate(dateString) {
  return new Date(dateString).toLocaleDateString('de-DE', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
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
      <button
        type="button"
        class="ml-4 underline"
        @click="goBack"
      >
        Zurück
      </button>
    </div>

    <!-- Content -->
    <template v-else-if="contact">
      <!-- Header -->
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-4">
          <button
            type="button"
            class="rounded-lg p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
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
          </button>
          <AvatarInitials
            :name="contact.name"
            :image-url="contact.avatar_url"
            size="xl"
          />
          <div>
            <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">
              {{ contact.name }}
            </h1>
            <p
              v-if="contact.position || contact.company_name"
              class="text-gray-500 dark:text-gray-400"
            >
              <span v-if="contact.position">{{ contact.position }}</span>
              <span v-if="contact.position && contact.company_name"> @ </span>
              <button
                v-if="contact.company_name"
                type="button"
                class="text-go4-primary hover:underline"
                @click="goToCompany"
              >
                {{ contact.company_name }}
              </button>
            </p>
            <div class="mt-1 flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
              <span>{{ contact.email }}</span>
              <span v-if="contact.phone">· {{ contact.phone }}</span>
            </div>
            <!-- Tags -->
            <div
              v-if="contact.tags?.length > 0"
              class="mt-2 flex flex-wrap gap-1"
            >
              <span
                v-for="tag in contact.tags"
                :key="tag"
                class="inline-flex rounded-full bg-go4-primary/10 px-2 py-0.5 text-xs text-go4-primary"
              >
                {{ tag }}
              </span>
            </div>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <button
            type="button"
            class="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600"
            @click="openEditModal"
          >
            Bearbeiten
          </button>
          <button
            type="button"
            class="rounded-lg border border-red-300 bg-white px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-50"
            @click="showDeleteDialog = true"
          >
            Löschen
          </button>
        </div>
      </div>

      <!-- Main Content -->
      <div class="mt-8 grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Left Column: Info -->
        <div class="lg:col-span-2 space-y-6">
          <!-- Quick Actions -->
          <div class="flex gap-3">
            <button
              type="button"
              class="flex items-center gap-2 rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark"
              @click="emailContact"
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
                  d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                />
              </svg>
              E-Mail senden
            </button>
            <button
              v-if="contact.phone"
              type="button"
              class="flex items-center gap-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600"
              @click="callContact"
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
                  d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"
                />
              </svg>
              Anrufen
            </button>
          </div>

          <!-- Contact Details Card -->
          <div class="rounded-lg bg-white dark:bg-gray-800 p-6 shadow-sm">
            <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
              Kontaktdaten
            </h2>
            <dl class="grid grid-cols-2 gap-4">
              <div>
                <dt class="text-sm text-gray-500 dark:text-gray-400">
                  E-Mail
                </dt>
                <dd class="text-sm text-gray-900 dark:text-gray-100">
                  {{ contact.email }}
                </dd>
              </div>
              <div>
                <dt class="text-sm text-gray-500 dark:text-gray-400">
                  Telefon
                </dt>
                <dd class="text-sm text-gray-900 dark:text-gray-100">
                  {{ contact.phone || '-' }}
                </dd>
              </div>
              <div>
                <dt class="text-sm text-gray-500 dark:text-gray-400">
                  Mobil
                </dt>
                <dd class="text-sm text-gray-900 dark:text-gray-100">
                  {{ contact.mobile || '-' }}
                </dd>
              </div>
              <div>
                <dt class="text-sm text-gray-500 dark:text-gray-400">
                  Position
                </dt>
                <dd class="text-sm text-gray-900 dark:text-gray-100">
                  {{ contact.position || '-' }}
                </dd>
              </div>
              <div v-if="contact.linkedin">
                <dt class="text-sm text-gray-500 dark:text-gray-400">
                  LinkedIn
                </dt>
                <dd>
                  <a
                    :href="contact.linkedin"
                    target="_blank"
                    class="text-sm text-go4-primary hover:underline"
                  >
                    Profil öffnen
                  </a>
                </dd>
              </div>
              <div v-if="contact.twitter">
                <dt class="text-sm text-gray-500 dark:text-gray-400">
                  Twitter
                </dt>
                <dd>
                  <a
                    :href="contact.twitter"
                    target="_blank"
                    class="text-sm text-go4-primary hover:underline"
                  >
                    Profil öffnen
                  </a>
                </dd>
              </div>
            </dl>
          </div>

          <!-- Notes -->
          <div
            v-if="contact.notes"
            class="rounded-lg bg-white dark:bg-gray-800 p-6 shadow-sm"
          >
            <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
              Notizen
            </h2>
            <p class="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
              {{ contact.notes }}
            </p>
          </div>
        </div>

        <!-- Right Column: Meta & Timeline -->
        <div class="space-y-6">
          <!-- Meta Info -->
          <div class="rounded-lg bg-white dark:bg-gray-800 p-6 shadow-sm">
            <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
              Details
            </h2>
            <dl class="space-y-3">
              <div>
                <dt class="text-sm text-gray-500 dark:text-gray-400">
                  Quelle
                </dt>
                <dd class="text-sm text-gray-900 dark:text-gray-100">
                  {{ contact.source || '-' }}
                </dd>
              </div>
              <div>
                <dt class="text-sm text-gray-500 dark:text-gray-400">
                  Erstellt
                </dt>
                <dd class="text-sm text-gray-900 dark:text-gray-100">
                  {{ formatDate(contact.created_at) }}
                </dd>
              </div>
              <div>
                <dt class="text-sm text-gray-500 dark:text-gray-400">
                  Aktualisiert
                </dt>
                <dd class="text-sm text-gray-900 dark:text-gray-100">
                  {{ formatDate(contact.updated_at) }}
                </dd>
              </div>
            </dl>
          </div>

          <!-- Activity Timeline -->
          <ActivityTimeline :contact-id="contactId" />
        </div>
      </div>
    </template>

    <!-- Edit Modal -->
    <ContactFormModal
      :open="showEditModal"
      :contact="contact"
      :companies="store.companies"
      :loading="modalLoading"
      @close="showEditModal = false"
      @save="saveContact"
    />

    <!-- Delete Confirmation -->
    <ConfirmDialog
      :open="showDeleteDialog"
      title="Kontakt löschen"
      :message="`Möchten Sie den Kontakt '${contact?.name}' wirklich löschen?`"
      confirm-text="Löschen"
      :loading="deleteLoading"
      @confirm="deleteContact"
      @cancel="showDeleteDialog = false"
    />
  </div>
</template>
