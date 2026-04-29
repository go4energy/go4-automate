<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useContactsStore } from '@/stores/contacts'
import { getContacts } from '@/api/contacts'
import PageHeader from '@/components/ui/PageHeader.vue'
import AvatarInitials from '@/components/ui/AvatarInitials.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'

const router = useRouter()
const route = useRoute()
const store = useContactsStore()

const showDeleteConfirm = ref(false)
const companyId = computed(() => route.params.id)

const company = computed(() => store.currentCompany)
// Local contacts list (the store keeps a global list which we don't want
// to overwrite when this view loads).
const contacts = ref([])
const contactsError = ref(null)

async function loadCompanyContacts(id) {
  contactsError.value = null
  try {
    const { data } = await getContacts({ company_id: id, limit: 200 })
    contacts.value = Array.isArray(data) ? data : (data.items || [])
  } catch (err) {
    contactsError.value = err.response?.data?.detail || err.message
    contacts.value = []
  }
}

onMounted(async () => {
  if (companyId.value) {
    try {
      await store.fetchCompanyDetail(companyId.value)
      await loadCompanyContacts(companyId.value)
    } catch (err) {
      console.error('Failed to load company:', err)
    }
  }
})

function editCompany() {
  // TODO: Open edit modal
}

function viewContact(contact) {
  router.push(`/contacts/people/${contact.id}`)
}

async function deleteCompany() {
  try {
    await store.removeCompany(companyId.value)
    router.push('/contacts')
  } catch {
    // Error in store
  }
}
</script>

<template>
  <div class="bg-go4-bg dark:bg-gray-900">
    <PageHeader
      :title="company?.name || 'Laden...'"
    >
      <template #actions>
        <div class="flex items-center gap-2">
          <button
            class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
            @click="editCompany"
          >
            Bearbeiten
          </button>
          <button
            class="rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 dark:border-red-800 dark:text-red-400 dark:hover:bg-red-900/20"
            @click="showDeleteConfirm = true"
          >
            Loeschen
          </button>
        </div>
      </template>
    </PageHeader>

    <div class="sm: lg:">
      <!-- Loading -->
      <div
        v-if="store.loading"
        class="flex items-center justify-center py-12"
      >
        <span class="text-go4-muted dark:text-gray-400">Laden...</span>
      </div>

      <!-- Error -->
      <div
        v-else-if="store.error"
        class="rounded-lg bg-red-50 p-4 text-red-700 dark:bg-red-900/30 dark:text-red-300"
      >
        {{ store.error }}
      </div>

      <!-- Content -->
      <div
        v-else-if="company"
        class="grid gap-6 lg:grid-cols-3"
      >
        <!-- Main Info -->
        <div class="lg:col-span-2 space-y-6">
          <!-- Company Card -->
          <div
            class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800"
          >
            <div class="flex items-start gap-4">
              <AvatarInitials
                :name="company.name"
                size="lg"
              />
              <div class="flex-1">
                <h2 class="text-xl font-semibold text-go4-secondary dark:text-white">
                  {{ company.name }}
                </h2>
                <p
                  v-if="company.industry"
                  class="text-go4-muted dark:text-gray-400"
                >
                  {{ company.industry }}
                </p>
              </div>
            </div>

            <div class="mt-6 grid gap-4 sm:grid-cols-2">
              <div v-if="company.website">
                <span class="text-xs font-medium uppercase text-go4-muted dark:text-gray-500">Website</span>
                <a
                  :href="company.website"
                  target="_blank"
                  class="block text-go4-primary hover:underline"
                >
                  {{ company.website }}
                </a>
              </div>
              <div v-if="company.phone">
                <span class="text-xs font-medium uppercase text-go4-muted dark:text-gray-500">Telefon</span>
                <p class="text-go4-secondary dark:text-white">
                  {{ company.phone }}
                </p>
              </div>
              <div v-if="company.email">
                <span class="text-xs font-medium uppercase text-go4-muted dark:text-gray-500">E-Mail</span>
                <a
                  :href="`mailto:${company.email}`"
                  class="block text-go4-primary hover:underline"
                >
                  {{ company.email }}
                </a>
              </div>
              <div v-if="company.size">
                <span class="text-xs font-medium uppercase text-go4-muted dark:text-gray-500">Groesse</span>
                <p class="text-go4-secondary dark:text-white">
                  {{ company.size }}
                </p>
              </div>
            </div>

            <div
              v-if="company.address"
              class="mt-4"
            >
              <span class="text-xs font-medium uppercase text-go4-muted dark:text-gray-500">Adresse</span>
              <p class="text-go4-secondary dark:text-white">
                {{ company.address.street }}<br v-if="company.address.street">
                {{ company.address.zip }} {{ company.address.city
                }}<br v-if="company.address.city">
                {{ company.address.country }}
              </p>
            </div>
          </div>

          <!-- Contacts -->
          <div
            class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800"
          >
            <h3 class="mb-4 font-medium text-go4-secondary dark:text-white">
              Kontakte ({{ contacts.length }})
            </h3>

            <div
              v-if="contacts.length === 0"
              class="py-8 text-center text-go4-muted dark:text-gray-400"
            >
              Keine Kontakte zugeordnet
            </div>

            <div
              v-else
              class="space-y-3"
            >
              <div
                v-for="contact in contacts"
                :key="contact.id"
                class="flex cursor-pointer items-center gap-3 rounded-lg p-3 hover:bg-gray-50 dark:hover:bg-gray-700"
                @click="viewContact(contact)"
              >
                <AvatarInitials
                  :name="contact.name"
                  size="sm"
                />
                <div class="flex-1">
                  <p class="font-medium text-go4-secondary dark:text-white">
                    {{ contact.name }}
                  </p>
                  <p class="text-sm text-go4-muted dark:text-gray-400">
                    {{ contact.position || contact.email }}
                  </p>
                </div>
                <svg
                  class="h-5 w-5 text-gray-400"
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
        </div>

        <!-- Sidebar -->
        <div class="space-y-6">
          <!-- Stats -->
          <div
            class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800"
          >
            <h3 class="mb-4 font-medium text-go4-secondary dark:text-white">
              Details
            </h3>
            <dl class="space-y-3 text-sm">
              <div class="flex justify-between">
                <dt class="text-go4-muted dark:text-gray-400">
                  Erstellt
                </dt>
                <dd class="text-go4-secondary dark:text-white">
                  {{ new Date(company.created_at).toLocaleDateString('de-DE') }}
                </dd>
              </div>
              <div
                v-if="company.source"
                class="flex justify-between"
              >
                <dt class="text-go4-muted dark:text-gray-400">
                  Quelle
                </dt>
                <dd class="text-go4-secondary dark:text-white">
                  {{ company.source }}
                </dd>
              </div>
            </dl>
          </div>

          <!-- Tags -->
          <div
            v-if="company.tags?.length"
            class="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800"
          >
            <h3 class="mb-4 font-medium text-go4-secondary dark:text-white">
              Tags
            </h3>
            <div class="flex flex-wrap gap-2">
              <span
                v-for="tag in company.tags"
                :key="tag"
                class="rounded-full bg-gray-100 px-2.5 py-0.5 text-xs text-gray-700 dark:bg-gray-700 dark:text-gray-300"
              >
                {{ tag }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Delete Confirmation -->
    <ConfirmDialog
      :open="showDeleteConfirm"
      title="Firma loeschen?"
      :message="`Moechtest du '${company?.name}' wirklich loeschen?`"
      confirm-text="Loeschen"
      variant="danger"
      @confirm="deleteCompany"
      @cancel="showDeleteConfirm = false"
    />
  </div>
</template>
