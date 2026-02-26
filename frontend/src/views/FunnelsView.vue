<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useFunnelsStore } from '@/stores/funnels'
import PageHeader from '@/components/ui/PageHeader.vue'
import SearchInput from '@/components/ui/SearchInput.vue'
import CardGrid from '@/components/ui/CardGrid.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import FunnelCard from '@/components/funnels/FunnelCard.vue'

const router = useRouter()
const store = useFunnelsStore()

const searchQuery = ref('')
const statusFilter = ref('')
const showCreateModal = ref(false)
const showDeleteConfirm = ref(false)
const funnelToDelete = ref(null)
const formData = ref({
  name: '',
  description: '',
  color: '#8B5CF6',
  status: 'active',
  tags: []
})
const formLoading = ref(false)

const colors = [
  '#8B5CF6', // Purple
  '#3B82F6', // Blue
  '#10B981', // Green
  '#F59E0B', // Amber
  '#EF4444', // Red
  '#EC4899', // Pink
  '#6366F1', // Indigo
  '#14B8A6' // Teal
]

const filteredFunnels = computed(() => {
  let result = store.funnels

  if (statusFilter.value) {
    result = result.filter((f) => f.status === statusFilter.value)
  }

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(
      (f) =>
        f.name.toLowerCase().includes(query) ||
        f.description?.toLowerCase().includes(query) ||
        f.tags?.some((t) => t.toLowerCase().includes(query))
    )
  }

  return result
})

import { computed } from 'vue'

onMounted(async () => {
  await store.fetchFunnels()
})

function openFunnel(funnel) {
  router.push(`/funnels/${funnel.id}`)
}

function openCreateModal() {
  formData.value = {
    name: '',
    description: '',
    color: '#8B5CF6',
    status: 'active',
    tags: []
  }
  showCreateModal.value = true
}

async function createFunnel() {
  if (!formData.value.name.trim()) return

  formLoading.value = true
  try {
    const funnel = await store.addFunnel(formData.value)
    showCreateModal.value = false
    router.push(`/funnels/${funnel.id}`)
  } finally {
    formLoading.value = false
  }
}

function confirmDelete(funnel) {
  funnelToDelete.value = funnel
  showDeleteConfirm.value = true
}

async function deleteFunnel() {
  if (!funnelToDelete.value) return

  try {
    await store.removeFunnel(funnelToDelete.value.id)
    showDeleteConfirm.value = false
    funnelToDelete.value = null
  } catch {
    // Error is in store
  }
}
</script>

<template>
  <div class="min-h-screen bg-go4-bg dark:bg-gray-900">
    <PageHeader
      title="Funnels"
      subtitle="Prospecting & Lead-Generierung"
    >
      <template #actions>
        <button
          class="flex items-center gap-2 rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark"
          @click="openCreateModal"
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
          Neuer Funnel
        </button>
      </template>
    </PageHeader>

    <div class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <!-- Filters -->
      <div class="mb-6 flex flex-wrap items-center gap-4">
        <SearchInput
          v-model="searchQuery"
          placeholder="Suchen..."
          class="w-64"
        />

        <select
          v-model="statusFilter"
          class="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
        >
          <option value="">
            Alle Status
          </option>
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

        <!-- Stats -->
        <div class="ml-auto flex items-center gap-4 text-sm text-go4-muted dark:text-gray-400">
          <span>{{ filteredFunnels.length }} Funnels</span>
          <span>{{ store.totalProspects }} Prospects</span>
        </div>
      </div>

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

      <!-- Empty State -->
      <EmptyState
        v-else-if="filteredFunnels.length === 0"
        title="Keine Funnels"
        description="Erstelle deinen ersten Funnel fuer Prospecting."
      >
        <button
          class="mt-4 rounded-lg bg-go4-primary px-4 py-2 text-sm text-white hover:bg-go4-primary-dark"
          @click="openCreateModal"
        >
          Funnel erstellen
        </button>
      </EmptyState>

      <!-- Funnel Grid -->
      <CardGrid
        v-else
        :columns="3"
      >
        <FunnelCard
          v-for="funnel in filteredFunnels"
          :key="funnel.id"
          :funnel="funnel"
          @click="openFunnel"
          @edit="openFunnel"
          @delete="confirmDelete"
        />
      </CardGrid>
    </div>

    <!-- Create Modal -->
    <Teleport to="body">
      <div
        v-if="showCreateModal"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
        @click.self="showCreateModal = false"
      >
        <div class="w-full max-w-md rounded-lg bg-white dark:bg-gray-800 p-6 shadow-xl">
          <h2 class="text-lg font-semibold text-go4-secondary dark:text-white mb-4">
            Neuer Funnel
          </h2>

          <form
            class="space-y-4"
            @submit.prevent="createFunnel"
          >
            <div>
              <label class="block text-sm font-medium text-go4-secondary dark:text-gray-200 mb-1">
                Name *
              </label>
              <input
                v-model="formData.name"
                type="text"
                required
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                placeholder="z.B. Energieversorger Q1"
              >
            </div>

            <div>
              <label class="block text-sm font-medium text-go4-secondary dark:text-gray-200 mb-1">
                Beschreibung
              </label>
              <textarea
                v-model="formData.description"
                rows="2"
                class="w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                placeholder="Optional"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-go4-secondary dark:text-gray-200 mb-1">
                Farbe
              </label>
              <div class="flex gap-2">
                <button
                  v-for="color in colors"
                  :key="color"
                  type="button"
                  class="h-8 w-8 rounded-full border-2 transition-transform hover:scale-110"
                  :class="{
                    'border-gray-800 dark:border-white': formData.color === color,
                    'border-transparent': formData.color !== color
                  }"
                  :style="{ backgroundColor: color }"
                  @click="formData.color = color"
                />
              </div>
            </div>

            <div class="flex justify-end gap-3 pt-4">
              <button
                type="button"
                class="rounded-lg px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
                @click="showCreateModal = false"
              >
                Abbrechen
              </button>
              <button
                type="submit"
                class="rounded-lg bg-go4-primary px-4 py-2 text-sm text-white hover:bg-go4-primary-dark disabled:opacity-50"
                :disabled="formLoading || !formData.name.trim()"
              >
                {{ formLoading ? 'Erstellen...' : 'Erstellen' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Delete Confirmation -->
    <ConfirmDialog
      :show="showDeleteConfirm"
      title="Funnel loeschen?"
      :message="`Möchtest du den Funnel '${funnelToDelete?.name}' wirklich löschen? Alle Prospects und Companies werden ebenfalls gelöscht.`"
      confirm-label="Loeschen"
      confirm-variant="danger"
      @confirm="deleteFunnel"
      @cancel="showDeleteConfirm = false"
    />
  </div>
</template>
