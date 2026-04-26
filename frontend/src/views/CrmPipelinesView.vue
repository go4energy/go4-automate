<script setup>
import { ref, onMounted } from 'vue'
import { useCrmStore } from '@/stores/crm'
import PageHeader from '@/components/ui/PageHeader.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import StageEditor from '@/components/crm/StageEditor.vue'

const store = useCrmStore()

// Modal state
const showPipelineModal = ref(false)
const editingPipeline = ref(null)
const pipelineForm = ref({ name: '', description: '', is_default: false })
const modalLoading = ref(false)

const showDeleteDialog = ref(false)
const deletingPipeline = ref(null)

const expandedPipelineId = ref(null)

onMounted(async () => {
  await store.fetchPipelines()
  // Expand first pipeline by default
  if (store.pipelines.length > 0) {
    expandedPipelineId.value = store.pipelines[0].id
    await store.fetchPipeline(store.pipelines[0].id)
  }
})

function openNewPipelineModal() {
  editingPipeline.value = null
  pipelineForm.value = { name: '', description: '', is_default: false }
  showPipelineModal.value = true
}

function openEditPipelineModal(pipeline) {
  editingPipeline.value = pipeline
  pipelineForm.value = {
    name: pipeline.name,
    description: pipeline.description || '',
    is_default: pipeline.is_default
  }
  showPipelineModal.value = true
}

async function savePipeline() {
  if (!pipelineForm.value.name.trim()) return

  modalLoading.value = true
  try {
    if (editingPipeline.value) {
      await store.editPipeline(editingPipeline.value.id, pipelineForm.value)
    } else {
      await store.addPipeline(pipelineForm.value)
    }
    showPipelineModal.value = false
    await store.fetchPipelines()
  } catch {
    // Error is set in store
  } finally {
    modalLoading.value = false
  }
}

function confirmDeletePipeline(pipeline) {
  deletingPipeline.value = pipeline
  showDeleteDialog.value = true
}

async function deletePipeline() {
  if (!deletingPipeline.value) return

  try {
    await store.removePipeline(deletingPipeline.value.id)
    showDeleteDialog.value = false
    deletingPipeline.value = null
  } catch {
    // Error is set in store
  }
}

async function toggleExpand(pipeline) {
  if (expandedPipelineId.value === pipeline.id) {
    expandedPipelineId.value = null
  } else {
    expandedPipelineId.value = pipeline.id
    await store.fetchPipeline(pipeline.id)
  }
}
</script>

<template>
  <div>
    <PageHeader
      title="Pipelines"
      subtitle="Sales Pipelines und Stages verwalten"
    >
      <template #actions>
        <button
          type="button"
          class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark"
          @click="openNewPipelineModal"
        >
          + Pipeline
        </button>
      </template>
    </PageHeader>

    <!-- Loading -->
    <div
      v-if="store.loading"
      class="mt-6 flex items-center justify-center p-12"
    >
      <span class="text-go4-muted dark:text-gray-400">Laden...</span>
    </div>

    <!-- Error -->
    <div
      v-else-if="store.error"
      class="mt-6 rounded-lg bg-red-50 dark:bg-red-900/20 p-4 text-red-700 dark:text-red-400"
    >
      {{ store.error }}
    </div>

    <!-- Empty State -->
    <div
      v-else-if="store.pipelines.length === 0"
      class="mt-6 flex flex-col items-center justify-center rounded-lg border border-dashed border-gray-300 dark:border-gray-600 p-12"
    >
      <svg
        class="h-12 w-12 text-gray-300 dark:text-gray-600 mb-4"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2"
        />
      </svg>
      <h3 class="text-lg font-medium text-gray-900 dark:text-gray-100 mb-1">
        Keine Pipelines
      </h3>
      <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
        Erstellen Sie Ihre erste Sales Pipeline.
      </p>
      <button
        type="button"
        class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark"
        @click="openNewPipelineModal"
      >
        + Pipeline erstellen
      </button>
    </div>

    <!-- Pipeline List -->
    <div
      v-else
      class="mt-6 space-y-4"
    >
      <div
        v-for="pipeline in store.pipelines"
        :key="pipeline.id"
        class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden"
      >
        <!-- Pipeline Header -->
        <div
          class="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50"
          @click="toggleExpand(pipeline)"
        >
          <div class="flex items-center gap-3">
            <svg
              class="h-5 w-5 text-gray-400 transition-transform"
              :class="{ 'rotate-90': expandedPipelineId === pipeline.id }"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M9 5l7 7-7 7"
              />
            </svg>
            <div>
              <div class="flex items-center gap-2">
                <h3 class="font-medium text-gray-900 dark:text-gray-100">
                  {{ pipeline.name }}
                </h3>
                <span
                  v-if="pipeline.is_default"
                  class="rounded-full bg-go4-primary/10 px-2 py-0.5 text-xs font-medium text-go4-primary"
                >
                  Standard
                </span>
              </div>
              <p
                v-if="pipeline.description"
                class="text-sm text-gray-500 dark:text-gray-400"
              >
                {{ pipeline.description }}
              </p>
            </div>
          </div>

          <div
            class="flex items-center gap-2"
            @click.stop
          >
            <span class="text-sm text-gray-500 dark:text-gray-400">
              {{ pipeline.stages?.length || 0 }} Stages · {{ pipeline.deal_count || 0 }} Deals
            </span>
            <button
              type="button"
              class="rounded p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-600"
              @click="openEditPipelineModal(pipeline)"
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
                  d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
                />
              </svg>
            </button>
            <button
              v-if="!pipeline.is_default"
              type="button"
              class="rounded p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20"
              @click="confirmDeletePipeline(pipeline)"
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
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                />
              </svg>
            </button>
          </div>
        </div>

        <!-- Stages (expanded) -->
        <div
          v-if="expandedPipelineId === pipeline.id && store.currentPipeline?.id === pipeline.id"
          class="border-t border-gray-200 dark:border-gray-700 p-4 bg-gray-50 dark:bg-gray-900/50"
        >
          <StageEditor :pipeline="store.currentPipeline" />
        </div>
      </div>
    </div>

    <!-- Pipeline Modal -->
    <Teleport to="body">
      <Transition
        enter-active-class="duration-200 ease-out"
        enter-from-class="opacity-0"
        enter-to-class="opacity-100"
        leave-active-class="duration-150 ease-in"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <div
          v-if="showPipelineModal"
          class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          @click.self="showPipelineModal = false"
        >
          <div class="w-full max-w-md rounded-lg bg-white dark:bg-gray-800 shadow-xl">
            <div
              class="flex items-center justify-between border-b border-gray-200 dark:border-gray-700 px-6 py-4"
            >
              <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {{ editingPipeline ? 'Pipeline bearbeiten' : 'Neue Pipeline' }}
              </h2>
              <button
                type="button"
                class="rounded-lg p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                @click="showPipelineModal = false"
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
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>

            <form
              class="p-6 space-y-4"
              @submit.prevent="savePipeline"
            >
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Name *
                </label>
                <input
                  v-model="pipelineForm.name"
                  type="text"
                  required
                  placeholder="z.B. Sales Pipeline"
                  class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
                >
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Beschreibung
                </label>
                <textarea
                  v-model="pipelineForm.description"
                  rows="2"
                  class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
                />
              </div>

              <div class="flex items-center gap-2">
                <input
                  id="is_default"
                  v-model="pipelineForm.is_default"
                  type="checkbox"
                  class="h-4 w-4 rounded border-gray-300 text-go4-primary focus:ring-go4-primary"
                >
                <label
                  for="is_default"
                  class="text-sm text-gray-700 dark:text-gray-300"
                >
                  Als Standard-Pipeline festlegen
                </label>
              </div>

              <div
                class="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700"
              >
                <button
                  type="button"
                  :disabled="modalLoading"
                  class="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50"
                  @click="showPipelineModal = false"
                >
                  Abbrechen
                </button>
                <button
                  type="submit"
                  :disabled="modalLoading"
                  class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark disabled:opacity-50"
                >
                  {{ modalLoading ? 'Speichern...' : 'Speichern' }}
                </button>
              </div>
            </form>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Delete Confirmation -->
    <ConfirmDialog
      :open="showDeleteDialog"
      title="Pipeline löschen"
      message="Möchten Sie diese Pipeline wirklich löschen? Alle Deals in dieser Pipeline werden ebenfalls gelöscht."
      confirm-text="Löschen"
      @confirm="deletePipeline"
      @cancel="showDeleteDialog = false"
    />
  </div>
</template>
