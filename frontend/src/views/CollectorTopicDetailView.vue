<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCollectorStore } from '@/stores/collector'
import { getPromptBySlug, updatePrompt } from '@/api/prompts'
import PageHeader from '@/components/ui/PageHeader.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import TagSelector from '@/components/ui/TagSelector.vue'
import StreamSelector from '@/components/ui/StreamSelector.vue'

const route = useRoute()
const router = useRouter()
const store = useCollectorStore()

const loading = ref(false)
const error = ref(null)
const saving = ref(false)
const reanalyzing = ref(false)

// Prompt section
const promptData = ref(null)
const promptLoading = ref(false)
const promptError = ref(null)
const promptEditing = ref(false)
const promptSaving = ref(false)
const editedSystemPrompt = ref('')
const editedUserPrompt = ref('')

// Metadata editing
const metaForm = ref({
  tags: [],
  streams: [],
  group_id: null
})

const topic = computed(() => store.currentTopic)

const priorityLabels = {
  1: 'Sehr hoch',
  2: 'Hoch',
  3: 'Normal',
  4: 'Niedrig',
  5: 'Sehr niedrig'
}

onMounted(async () => {
  await loadTopic()
  if (store.groups.length === 0) {
    await store.fetchGroups()
  }
})

async function loadTopic() {
  loading.value = true
  error.value = null
  try {
    const id = Number(route.params.id)
    await store.fetchTopic(id)
    syncMetaForm()
    if (store.currentTopic?.prompt_slug) {
      await loadPrompt(store.currentTopic.prompt_slug)
    }
  } catch (err) {
    error.value = err.response?.data?.detail || err.message
  } finally {
    loading.value = false
  }
}

function syncMetaForm() {
  if (!store.currentTopic) return
  metaForm.value = {
    tags: [...(store.currentTopic.tags || [])],
    streams: [...(store.currentTopic.streams || [])],
    group_id: store.currentTopic.group_id
  }
}

async function loadPrompt(slug) {
  promptLoading.value = true
  promptError.value = null
  try {
    const { data } = await getPromptBySlug(slug)
    promptData.value = data
  } catch (err) {
    promptError.value = err.response?.data?.detail || 'Prompt nicht gefunden'
  } finally {
    promptLoading.value = false
  }
}

async function handleApprove() {
  await store.editTopic(topic.value.id, { status: 'approved' })
  await store.fetchTopic(topic.value.id)
}

async function handleReject() {
  await store.editTopic(topic.value.id, { status: 'rejected' })
  await store.fetchTopic(topic.value.id)
}

async function handleSaveMeta() {
  saving.value = true
  error.value = null
  try {
    await store.editTopic(topic.value.id, {
      tags: metaForm.value.tags,
      streams: metaForm.value.streams,
      group_id: metaForm.value.group_id
    })
    await store.fetchTopic(topic.value.id)
  } catch (err) {
    error.value = err.response?.data?.detail || err.message
  } finally {
    saving.value = false
  }
}

function startPromptEdit() {
  if (!promptData.value) return
  editedSystemPrompt.value = promptData.value.system_prompt || ''
  editedUserPrompt.value = promptData.value.user_prompt || ''
  promptEditing.value = true
}

function cancelPromptEdit() {
  promptEditing.value = false
}

async function handleSavePrompt() {
  if (!promptData.value) return
  promptSaving.value = true
  try {
    const { data } = await updatePrompt(promptData.value.id, {
      system_prompt: editedSystemPrompt.value,
      user_prompt: editedUserPrompt.value
    })
    promptData.value = data
    promptEditing.value = false
  } catch (err) {
    promptError.value = err.response?.data?.detail || err.message
  } finally {
    promptSaving.value = false
  }
}

async function handleReanalyze() {
  reanalyzing.value = true
  error.value = null
  try {
    await store.triggerReanalyze(topic.value.id)
    await store.fetchTopic(topic.value.id)
  } catch (err) {
    error.value = err.response?.data?.detail || err.message
  } finally {
    reanalyzing.value = false
  }
}
</script>

<template>
  <div>
    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-16">
      <span class="text-go4-muted dark:text-gray-400">Laden...</span>
    </div>

    <!-- Error -->
    <div
      v-else-if="error && !topic"
      class="rounded-lg bg-red-50 dark:bg-red-900/20 p-4 text-sm text-red-700 dark:text-red-400"
    >
      {{ error }}
    </div>

    <!-- Content -->
    <div v-else-if="topic">
      <!-- 1. Header -->
      <PageHeader :title="topic.title" subtitle="Thema-Detail">
        <template #actions>
          <button
            class="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm font-medium text-go4-secondary dark:text-gray-100 hover:bg-gray-50 dark:hover:bg-gray-700"
            @click="router.push('/collector')"
          >
            Zurueck
          </button>
          <template v-if="topic.status === 'suggested'">
            <button
              class="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700"
              @click="handleApprove"
            >
              Genehmigen
            </button>
            <button
              class="rounded-lg bg-red-100 dark:bg-red-900/20 px-4 py-2 text-sm font-medium text-red-700 dark:text-red-400 hover:bg-red-200"
              @click="handleReject"
            >
              Ablehnen
            </button>
          </template>
          <StatusBadge :status="topic.status" />
        </template>
      </PageHeader>

      <!-- Error banner -->
      <div
        v-if="error"
        class="mt-4 rounded-lg bg-red-50 dark:bg-red-900/20 p-3 text-sm text-red-700 dark:text-red-400"
      >
        {{ error }}
      </div>

      <div class="mt-6 space-y-6">
        <!-- 2. Zusammenfassung -->
        <div class="rounded-lg bg-white dark:bg-gray-800 p-6 shadow-sm">
          <h3
            class="text-sm font-semibold uppercase tracking-wider text-go4-muted dark:text-gray-400"
          >
            Kurzfassung
          </h3>
          <p class="mt-2 text-sm text-go4-secondary dark:text-gray-100">
            {{ topic.description }}
          </p>

          <div v-if="topic.detail" class="mt-4">
            <h3
              class="text-sm font-semibold uppercase tracking-wider text-go4-muted dark:text-gray-400"
            >
              Langfassung
            </h3>
            <p class="mt-2 whitespace-pre-line text-sm text-go4-secondary dark:text-gray-200">
              {{ topic.detail }}
            </p>
          </div>
        </div>

        <!-- 3. Quellartikel -->
        <div class="rounded-lg bg-white dark:bg-gray-800 p-6 shadow-sm">
          <h3
            class="text-sm font-semibold uppercase tracking-wider text-go4-muted dark:text-gray-400"
          >
            Quellartikel
          </h3>
          <div v-if="topic.finding_url" class="mt-2">
            <p
              v-if="topic.finding_title"
              class="text-sm font-medium text-go4-secondary dark:text-gray-100"
            >
              {{ topic.finding_title }}
            </p>
            <a
              :href="topic.finding_url"
              target="_blank"
              class="mt-1 inline-flex items-center gap-1 text-sm text-go4-primary hover:underline"
            >
              <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                />
              </svg>
              Quellartikel oeffnen
            </a>
          </div>
          <p v-else class="mt-2 text-sm text-go4-muted dark:text-gray-400">
            Kein Quellartikel vorhanden (manuelles Thema).
          </p>
        </div>

        <!-- 4. Metadaten (editierbar) -->
        <div class="rounded-lg bg-white dark:bg-gray-800 p-6 shadow-sm">
          <h3
            class="text-sm font-semibold uppercase tracking-wider text-go4-muted dark:text-gray-400"
          >
            Metadaten
          </h3>

          <div class="mt-4 grid gap-4 md:grid-cols-2">
            <!-- Tags -->
            <div>
              <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100"
                >Tags</label
              >
              <div class="mt-1">
                <TagSelector v-model="metaForm.tags" />
              </div>
            </div>

            <!-- Streams -->
            <div>
              <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100"
                >Streams</label
              >
              <div class="mt-1">
                <StreamSelector v-model="metaForm.streams" />
              </div>
            </div>

            <!-- Gruppe -->
            <div>
              <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100"
                >Gruppe</label
              >
              <select
                v-model="metaForm.group_id"
                class="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm dark:text-gray-100"
              >
                <option :value="null">Keine Gruppe</option>
                <option v-for="g in store.groups" :key="g.id" :value="g.id">
                  {{ g.name }}
                </option>
              </select>
            </div>

            <!-- Status + Prioritaet (read-only) -->
            <div class="flex gap-6">
              <div>
                <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100"
                  >Status</label
                >
                <div class="mt-1.5">
                  <StatusBadge :status="topic.status" />
                </div>
              </div>
              <div>
                <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100"
                  >Prioritaet</label
                >
                <p class="mt-1.5 text-sm text-go4-secondary dark:text-gray-200">
                  {{ priorityLabels[topic.priority] || '-' }}
                </p>
              </div>
            </div>
          </div>

          <div class="mt-4 flex justify-end">
            <button
              :disabled="saving"
              class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary/90 disabled:opacity-50"
              @click="handleSaveMeta"
            >
              {{ saving ? 'Speichern...' : 'Metadaten speichern' }}
            </button>
          </div>
        </div>

        <!-- 5. Prompt-Sektion -->
        <div class="rounded-lg bg-white dark:bg-gray-800 p-6 shadow-sm">
          <h3
            class="text-sm font-semibold uppercase tracking-wider text-go4-muted dark:text-gray-400"
          >
            Analyse-Prompt
          </h3>

          <!-- Kein Prompt -->
          <div v-if="!topic.prompt_slug" class="mt-2">
            <p class="text-sm text-go4-muted dark:text-gray-400">
              Kein Prompt verknuepft (manuelles Thema).
            </p>
          </div>

          <!-- Prompt loading -->
          <div v-else-if="promptLoading" class="mt-2">
            <span class="text-sm text-go4-muted dark:text-gray-400">Prompt laden...</span>
          </div>

          <!-- Prompt error -->
          <div
            v-else-if="promptError"
            class="mt-2 rounded-lg bg-red-50 dark:bg-red-900/20 p-3 text-sm text-red-700 dark:text-red-400"
          >
            {{ promptError }}
          </div>

          <!-- Prompt loaded -->
          <div v-else-if="promptData" class="mt-3 space-y-4">
            <!-- Info chips -->
            <div class="flex flex-wrap gap-2">
              <span
                class="rounded-full bg-gray-100 dark:bg-gray-700 px-3 py-1 text-xs text-gray-600 dark:text-gray-300"
              >
                Model: {{ promptData.model }}
              </span>
              <span
                class="rounded-full bg-gray-100 dark:bg-gray-700 px-3 py-1 text-xs text-gray-600 dark:text-gray-300"
              >
                Temperature: {{ promptData.temperature }}
              </span>
              <span
                class="rounded-full bg-gray-100 dark:bg-gray-700 px-3 py-1 text-xs text-gray-600 dark:text-gray-300"
              >
                Provider: {{ promptData.provider }}
              </span>
            </div>

            <!-- Read-only mode -->
            <div v-if="!promptEditing">
              <div>
                <label class="text-xs font-medium text-go4-muted dark:text-gray-400"
                  >System-Prompt</label
                >
                <pre
                  class="mt-1 max-h-48 overflow-auto whitespace-pre-wrap rounded-lg bg-gray-50 dark:bg-gray-900 p-3 text-xs text-go4-secondary dark:text-gray-200"
                  >{{ promptData.system_prompt }}</pre
                >
              </div>
              <div class="mt-3">
                <label class="text-xs font-medium text-go4-muted dark:text-gray-400"
                  >User-Prompt</label
                >
                <pre
                  class="mt-1 max-h-48 overflow-auto whitespace-pre-wrap rounded-lg bg-gray-50 dark:bg-gray-900 p-3 text-xs text-go4-secondary dark:text-gray-200"
                  >{{ promptData.user_prompt }}</pre
                >
              </div>
            </div>

            <!-- Edit mode -->
            <div v-else>
              <div>
                <label class="text-xs font-medium text-go4-muted dark:text-gray-400"
                  >System-Prompt</label
                >
                <textarea
                  v-model="editedSystemPrompt"
                  rows="6"
                  class="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-xs font-mono dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
                />
              </div>
              <div class="mt-3">
                <label class="text-xs font-medium text-go4-muted dark:text-gray-400"
                  >User-Prompt</label
                >
                <textarea
                  v-model="editedUserPrompt"
                  rows="10"
                  class="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-xs font-mono dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
                />
              </div>
            </div>

            <!-- Actions -->
            <div class="flex items-center gap-2 pt-2">
              <template v-if="!promptEditing">
                <button
                  class="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm font-medium text-go4-secondary dark:text-gray-100 hover:bg-gray-50 dark:hover:bg-gray-700"
                  @click="startPromptEdit"
                >
                  Bearbeiten
                </button>
              </template>
              <template v-else>
                <button
                  :disabled="promptSaving"
                  class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary/90 disabled:opacity-50"
                  @click="handleSavePrompt"
                >
                  {{ promptSaving ? 'Speichern...' : 'Prompt speichern' }}
                </button>
                <button
                  class="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm font-medium text-go4-secondary dark:text-gray-100 hover:bg-gray-50 dark:hover:bg-gray-700"
                  @click="cancelPromptEdit"
                >
                  Abbrechen
                </button>
              </template>
              <button
                :disabled="reanalyzing"
                class="rounded-lg bg-amber-500 px-4 py-2 text-sm font-medium text-white hover:bg-amber-600 disabled:opacity-50"
                @click="handleReanalyze"
              >
                {{ reanalyzing ? 'Analysiert...' : 'Neu analysieren' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
