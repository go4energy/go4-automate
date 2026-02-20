<script setup>
import { ref, onMounted } from 'vue'
import { useCrmStore } from '@/stores/crm'
import PageHeader from '@/components/ui/PageHeader.vue'
import EmptyState from '@/components/ui/EmptyState.vue'

const store = useCrmStore()
const statusFilter = ref('')

async function loadContacts() {
  const params = {}
  if (statusFilter.value) {
    params.status = statusFilter.value
  }
  await store.fetchContacts(params)
}

async function changeStatus(contactId, status) {
  try {
    await store.changeStatus(contactId, status)
  } catch {
    // error is set in store
  }
}

async function togglePause(contact) {
  try {
    await store.toggleFollowupPause(contact.id, !contact.followup_paused)
  } catch {
    // error is set in store
  }
}

function applyFilter() {
  loadContacts()
}

onMounted(() => {
  loadContacts()
})
</script>

<template>
  <div>
    <PageHeader title="CRM" :subtitle="`${store.totalContacts} Kontakte gesamt`" />

    <!-- Filter -->
    <div class="mt-6 flex items-center gap-4">
      <select
        v-model="statusFilter"
        class="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
        @change="applyFilter"
      >
        <option value="">Alle Status</option>
        <option value="new">Neu</option>
        <option value="contacted">Kontaktiert</option>
        <option value="qualified">Qualifiziert</option>
        <option value="converted">Konvertiert</option>
        <option value="lost">Verloren</option>
      </select>
    </div>

    <!-- Loading -->
    <div v-if="store.loading" class="mt-8 flex items-center justify-center p-8">
      <span class="text-go4-muted">Laden...</span>
    </div>

    <!-- Error -->
    <div v-else-if="store.error" class="mt-8 rounded-lg bg-red-50 p-4 text-red-700">
      {{ store.error }}
    </div>

    <!-- Empty State -->
    <div v-else-if="store.contacts.length === 0" class="mt-8">
      <EmptyState title="Keine Kontakte gefunden" />
    </div>

    <!-- Table -->
    <div v-else class="mt-6 overflow-hidden rounded-lg bg-white shadow-sm">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th
              class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-go4-muted"
            >
              Name
            </th>
            <th
              class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-go4-muted"
            >
              E-Mail
            </th>
            <th
              class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-go4-muted"
            >
              Quelle
            </th>
            <th
              class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-go4-muted"
            >
              Score
            </th>
            <th
              class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-go4-muted"
            >
              Status
            </th>
            <th
              class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-go4-muted"
            >
              Follow-up
            </th>
            <th
              class="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-go4-muted"
            >
              Aktionen
            </th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-200 bg-white">
          <tr v-for="contact in store.contacts" :key="contact.id" class="hover:bg-gray-50">
            <td class="whitespace-nowrap px-6 py-4 text-sm font-medium text-go4-secondary">
              {{ contact.name }}
            </td>
            <td class="whitespace-nowrap px-6 py-4 text-sm text-go4-muted">
              {{ contact.email }}
            </td>
            <td class="whitespace-nowrap px-6 py-4 text-sm text-go4-muted">
              {{ contact.source || '-' }}
            </td>
            <td class="whitespace-nowrap px-6 py-4 text-sm">
              <span
                class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
                :class="{
                  'bg-red-100 text-red-800': contact.score >= 80,
                  'bg-yellow-100 text-yellow-800': contact.score >= 40 && contact.score < 80,
                  'bg-gray-100 text-gray-800': contact.score < 40
                }"
              >
                {{ contact.score }}
              </span>
            </td>
            <td class="whitespace-nowrap px-6 py-4 text-sm">
              <select
                :value="contact.status"
                class="rounded border border-gray-300 px-2 py-1 text-xs focus:border-go4-primary focus:outline-none"
                @change="changeStatus(contact.id, $event.target.value)"
              >
                <option value="new">Neu</option>
                <option value="contacted">Kontaktiert</option>
                <option value="qualified">Qualifiziert</option>
                <option value="converted">Konvertiert</option>
                <option value="lost">Verloren</option>
              </select>
            </td>
            <td class="whitespace-nowrap px-6 py-4 text-sm">
              <button
                class="rounded px-2 py-1 text-xs font-medium"
                :class="
                  contact.followup_paused
                    ? 'bg-yellow-100 text-yellow-800'
                    : 'bg-green-100 text-green-800'
                "
                @click="togglePause(contact)"
              >
                {{ contact.followup_paused ? 'Pausiert' : 'Aktiv' }}
              </button>
            </td>
            <td class="whitespace-nowrap px-6 py-4 text-sm text-go4-muted">
              Step {{ contact.followup_step }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
