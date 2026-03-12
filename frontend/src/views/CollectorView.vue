<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useCollectorStore } from '@/stores/collector'
import { getPromptBySlug } from '@/api/prompts'
import PageHeader from '@/components/ui/PageHeader.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import EmptyState from '@/components/ui/EmptyState.vue'

const router = useRouter()
const route = useRoute()
const store = useCollectorStore()

// Tab state from route
const activeTab = computed(() => route.meta?.tab || 'sources')

// Group modal
const showGroupModal = ref(false)
const editingGroup = ref(null)
const groupForm = ref({ name: '', slug: '', description: '', fetch_interval_hours: 24, tags: [] })
const groupSaving = ref(false)
const groupError = ref(null)

// Group settings dropdown
const showGroupMenu = ref(false)

// Prompts tab state (multi-prompt)
const promptsData = ref([])
const promptsLoading = ref(false)
const promptsError = ref(null)
const runningPromptSlug = ref(null)
const showAddPromptModal = ref(false)
const addPromptForm = ref({ purpose: '' })
const addPromptSaving = ref(false)
const addPromptError = ref(null)
const duplicateSourceSlug = ref(null)

// Selection state for bulk operations
const selectedFindingIds = ref(new Set())
const selectedTopicIds = ref(new Set())

// Filter state
const showAllFindings = ref(false)
const showAllTopics = ref(false)

const filteredFindings = computed(() => {
  if (showAllFindings.value) return store.findings
  return store.findings.filter((f) => f.status !== 'dismissed' && f.status !== 'used')
})

const filteredTopics = computed(() => {
  if (showAllTopics.value) return store.topics
  return store.topics.filter((t) => t.status !== 'rejected')
})

const tabs = [
  { key: 'sources', label: 'Quellen', route: '/collector/sources' },
  { key: 'findings', label: 'Findings', route: '/collector/findings' },
  { key: 'prompts', label: 'KI', route: '/collector/prompts' },
  { key: 'topics', label: 'Themen', route: '/collector/topics' }
]

const sourceTypeBadge = {
  rss: 'bg-orange-100 text-orange-800',
  website: 'bg-blue-100 text-blue-800',
  websearch: 'bg-purple-100 text-purple-800',
  inbox: 'bg-green-100 text-green-800'
}

const priorityLabels = ['', 'Sehr hoch', 'Hoch', 'Normal', 'Niedrig', 'Sehr niedrig']

onMounted(async () => {
  await store.fetchGroups()
  await loadGroupData()
})

watch(
  () => store.activeGroupId,
  async () => {
    await loadGroupData()
  }
)

watch(activeTab, (tab) => {
  if (tab === 'prompts') {
    loadGroupPrompts()
  }
})

async function loadGroupData() {
  selectedFindingIds.value = new Set()
  selectedTopicIds.value = new Set()
  await Promise.all([store.fetchSources(), store.fetchFindings(), store.fetchTopics()])
  if (activeTab.value === 'prompts') {
    await loadGroupPrompts()
  }
}

async function loadGroupPrompts() {
  const slugs = store.activeGroup?.analysis_prompt_slugs || []
  if (slugs.length === 0) {
    promptsData.value = []
    promptsError.value = null
    return
  }
  promptsLoading.value = true
  promptsError.value = null
  try {
    const results = await Promise.all(
      slugs.map((slug) =>
        getPromptBySlug(slug)
          .then((r) => r.data)
          .catch(() => null)
      )
    )
    promptsData.value = results.filter(Boolean)
  } catch (err) {
    promptsData.value = []
    promptsError.value = err.response?.data?.detail || err.message
  } finally {
    promptsLoading.value = false
  }
}

async function handleRunGroupPrompt(promptSlug) {
  if (!store.activeGroup) return
  runningPromptSlug.value = promptSlug
  try {
    await store.runPromptForGroup(store.activeGroup.id, promptSlug)
  } finally {
    runningPromptSlug.value = null
  }
}

async function handleAddPrompt() {
  if (!store.activeGroup) return
  addPromptSaving.value = true
  addPromptError.value = null
  try {
    await store.addPromptToGroup(
      store.activeGroup.id,
      addPromptForm.value.purpose,
      duplicateSourceSlug.value
    )
    showAddPromptModal.value = false
    addPromptForm.value = { purpose: '' }
    duplicateSourceSlug.value = null
    await loadGroupPrompts()
  } catch (err) {
    addPromptError.value = err.response?.data?.detail || err.message
  } finally {
    addPromptSaving.value = false
  }
}

async function handleRemovePrompt(promptSlug) {
  if (!store.activeGroup) return
  if (!confirm(`Prompt "${promptSlug}" wirklich entfernen? Zugehoerige Topics werden geloescht.`))
    return
  try {
    await store.removePromptFromGroup(store.activeGroup.id, promptSlug)
    await loadGroupPrompts()
  } catch {
    // error is set by store
  }
}

function openAddPromptModal() {
  addPromptForm.value = { purpose: '' }
  addPromptError.value = null
  duplicateSourceSlug.value = null
  showAddPromptModal.value = true
}

function openDuplicatePromptModal(sourceSlug) {
  addPromptForm.value = { purpose: '' }
  addPromptError.value = null
  duplicateSourceSlug.value = sourceSlug
  showAddPromptModal.value = true
}

const addPromptSlugPreview = computed(() => {
  const purpose = addPromptForm.value.purpose
  const groupSlug = store.activeGroup?.slug || '...'
  return purpose ? `${purpose}-${groupSlug}` : ''
})

// --- Selection helpers ---

function toggleFindingSelect(id) {
  const s = new Set(selectedFindingIds.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  selectedFindingIds.value = s
}

function toggleAllFindings() {
  if (selectedFindingIds.value.size === filteredFindings.value.length) {
    selectedFindingIds.value = new Set()
  } else {
    selectedFindingIds.value = new Set(filteredFindings.value.map((f) => f.id))
  }
}

function toggleTopicSelect(id) {
  const s = new Set(selectedTopicIds.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  selectedTopicIds.value = s
}

function toggleAllTopics() {
  if (selectedTopicIds.value.size === filteredTopics.value.length) {
    selectedTopicIds.value = new Set()
  } else {
    selectedTopicIds.value = new Set(filteredTopics.value.map((t) => t.id))
  }
}

async function handleBulkDeleteFindings() {
  const ids = [...selectedFindingIds.value]
  if (!ids.length) return
  if (!confirm(`${ids.length} Finding(s) wirklich loeschen?`)) return
  try {
    await store.removeFindings(ids)
    selectedFindingIds.value = new Set()
  } catch {
    // error is set by store
  }
}

async function handleBulkDeleteTopics() {
  const ids = [...selectedTopicIds.value]
  if (!ids.length) return
  if (!confirm(`${ids.length} Thema/Themen wirklich loeschen?`)) return
  try {
    await store.removeTopics(ids)
    selectedTopicIds.value = new Set()
  } catch {
    // error is set by store
  }
}

function handleSelectGroup(groupId) {
  store.selectGroup(groupId)
}

function openCreateGroupModal() {
  editingGroup.value = null
  groupForm.value = { name: '', slug: '', description: '', fetch_interval_hours: 24, tags: [] }
  groupError.value = null
  showGroupModal.value = true
}

function openEditGroupModal() {
  showGroupMenu.value = false
  const group = store.activeGroup
  if (!group) return
  editingGroup.value = group
  groupForm.value = {
    name: group.name,
    slug: group.slug,
    description: group.description || '',
    fetch_interval_hours: group.fetch_interval_hours || 24,
    tags: group.tags || []
  }
  groupError.value = null
  showGroupModal.value = true
}

function generateSlug() {
  if (!editingGroup.value) {
    groupForm.value.slug = groupForm.value.name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '')
  }
}

async function handleGroupSubmit() {
  groupSaving.value = true
  groupError.value = null
  try {
    if (editingGroup.value) {
      await store.editGroup(editingGroup.value.id, {
        name: groupForm.value.name,
        description: groupForm.value.description || null,
        fetch_interval_hours: groupForm.value.fetch_interval_hours,
        tags: groupForm.value.tags
      })
    } else {
      const group = await store.addGroup(groupForm.value)
      store.selectGroup(group.id)
    }
    showGroupModal.value = false
    await store.fetchGroups()
  } catch (err) {
    groupError.value = err.response?.data?.detail || err.message
  } finally {
    groupSaving.value = false
  }
}

async function handleDeleteGroup() {
  showGroupMenu.value = false
  if (!store.activeGroup) return
  const name = store.activeGroup.name
  if (!confirm(`Gruppe "${name}" wirklich loeschen? Sources/Findings/Topics bleiben erhalten.`))
    return
  try {
    await store.removeGroup(store.activeGroup.id)
    await store.fetchGroups()
    await loadGroupData()
  } catch {
    // error is set by store
  }
}

async function handleRunCollector(sourceId = null) {
  await store.triggerCollector(sourceId)
}

async function handleApproveTopic(topicId) {
  await store.editTopic(topicId, { status: 'approved' })
}

async function handleRejectTopic(topicId) {
  await store.editTopic(topicId, { status: 'rejected' })
}

async function handleDismissFinding(findingId) {
  await store.changeFindingStatus(findingId, 'dismissed')
}

async function handleReviewFinding(findingId) {
  await store.changeFindingStatus(findingId, 'reviewed')
}

async function handleChangeFindingGroup(findingId, event) {
  const groupId = Number(event.target.value)
  await store.changeFindingGroup(findingId, groupId)
  await store.fetchGroups()
}

async function handleToggleSource(source) {
  await store.editSource(source.id, { active: !source.active })
}

function openFindingUrl(finding) {
  if (finding.url) {
    window.open(finding.url, '_blank')
  }
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<template>
  <div>
    <PageHeader
      title="Collector"
      subtitle="Quellen scannen, Findings sammeln, Topics generieren"
    >
      <template #actions>
        <button
          class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90 disabled:opacity-50"
          :disabled="store.loading"
          @click="handleRunCollector()"
        >
          {{ store.loading ? 'Sammlung laeuft...' : 'Collector starten' }}
        </button>
        <router-link
          to="/collector/topics/new"
          class="rounded-lg border border-go4-primary px-4 py-2 text-sm font-medium text-go4-primary transition hover:bg-go4-primary/5"
        >
          Eigenes Thema
        </router-link>
      </template>
    </PageHeader>

    <!-- Group Selector -->
    <div class="mt-4 flex items-center gap-2 flex-wrap">
      <button
        v-for="group in store.groups"
        :key="group.id"
        class="rounded-full px-4 py-1.5 text-sm font-medium transition"
        :class="
          store.activeGroupId === group.id
            ? 'bg-go4-primary text-white'
            : 'bg-gray-100 dark:bg-gray-700 text-go4-secondary dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-600'
        "
        @click="handleSelectGroup(group.id)"
      >
        {{ group.name }}
        <span class="ml-1 text-xs opacity-70">
          {{ group.source_count + group.finding_count + group.topic_count }}
        </span>
      </button>
      <button
        class="rounded-full border-2 border-dashed border-gray-300 dark:border-gray-600 px-3 py-1.5 text-sm text-go4-muted dark:text-gray-400 transition hover:border-go4-primary hover:text-go4-primary"
        @click="openCreateGroupModal"
      >
        + Neue Gruppe
      </button>
      <!-- Group settings -->
      <div
        v-if="store.activeGroup"
        class="relative ml-1"
      >
        <button
          class="rounded-full p-1.5 text-go4-muted dark:text-gray-400 transition hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-go4-secondary"
          @click="showGroupMenu = !showGroupMenu"
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
              d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
            />
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
            />
          </svg>
        </button>
        <div
          v-if="showGroupMenu"
          class="absolute right-0 z-10 mt-1 w-40 rounded-lg bg-white dark:bg-gray-800 shadow-lg ring-1 ring-gray-200 dark:ring-gray-700"
          @click="showGroupMenu = false"
        >
          <button
            class="block w-full px-4 py-2 text-left text-sm text-go4-secondary dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-t-lg"
            @click="openEditGroupModal"
          >
            Bearbeiten
          </button>
          <button
            class="block w-full px-4 py-2 text-left text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-b-lg"
            @click="handleDeleteGroup"
          >
            Loeschen
          </button>
        </div>
      </div>
    </div>

    <!-- Run Result -->
    <div
      v-if="store.runResult"
      class="mt-4 rounded-lg p-4 text-sm"
      :class="
        store.runResult.findings_count === 0 && store.runResult.suggestions_count === 0
          ? 'bg-amber-50 text-amber-800'
          : 'bg-green-50 text-green-800'
      "
    >
      <template
        v-if="
          store.runResult.findings_count === 0 &&
            store.runResult.suggestions_count === 0 &&
            store.sources.length === 0
        "
      >
        Keine Quellen konfiguriert. Lege zuerst unter
        <router-link
          to="/collector/sources"
          class="font-medium underline"
        >
          Quellen
        </router-link>
        eine RSS-, Website- oder Websearch-Quelle an.
      </template>
      <template v-else>
        Collector abgeschlossen: {{ store.runResult.findings_count }} neue Findings,
        {{ store.runResult.suggestions_count }} Topic-Vorschlaege
        <span
          v-if="store.runResult.errors.length > 0"
          class="ml-2 text-red-600"
        >
          ({{ store.runResult.errors.length }} Fehler)
        </span>
      </template>
    </div>

    <!-- Error -->
    <div
      v-if="store.error"
      class="mt-4 rounded-lg bg-red-50 dark:bg-red-900/20 p-4 text-sm text-red-700 dark:text-red-400"
    >
      {{ store.error }}
    </div>

    <!-- Tabs with arrow separators -->
    <div class="mt-4 border-b border-gray-200 dark:border-gray-700">
      <nav class="-mb-px flex items-center">
        <template
          v-for="(tab, index) in tabs"
          :key="tab.key"
        >
          <router-link
            :to="tab.route"
            class="border-b-2 px-1 pb-3 text-sm font-medium transition"
            :class="
              activeTab === tab.key
                ? 'border-go4-primary text-go4-primary'
                : 'border-transparent text-go4-muted dark:text-gray-400 hover:border-gray-300 dark:hover:border-gray-600 hover:text-go4-secondary dark:hover:text-gray-100'
            "
          >
            {{ tab.label }}
            <span
              v-if="tab.key === 'topics'"
              class="ml-1.5 rounded-full bg-go4-primary/10 px-2 py-0.5 text-xs text-go4-primary"
            >
              {{ store.suggestedTopics.length }}
            </span>
            <span
              v-if="tab.key === 'findings'"
              class="ml-1.5 rounded-full bg-gray-100 dark:bg-gray-700 px-2 py-0.5 text-xs text-gray-600 dark:text-gray-300"
            >
              {{ store.newFindings.length }}
            </span>
            <span
              v-if="tab.key === 'sources'"
              class="ml-1.5 rounded-full bg-gray-100 dark:bg-gray-700 px-2 py-0.5 text-xs text-gray-600 dark:text-gray-300"
            >
              {{ store.sources.length }}
            </span>
          </router-link>
          <span
            v-if="index < tabs.length - 1"
            class="mx-3 pb-3 text-go4-muted dark:text-gray-500 select-none"
          >
            &rarr;
          </span>
        </template>
      </nav>
    </div>

    <!-- Loading -->
    <div
      v-if="store.loading"
      class="mt-8 flex items-center justify-center py-12"
    >
      <span class="text-go4-muted dark:text-gray-400">Laden...</span>
    </div>

    <!-- ==================== Topics Tab ==================== -->
    <div
      v-else-if="activeTab === 'topics'"
      class="mt-6"
    >
      <EmptyState
        v-if="store.topics.length === 0"
        title="Noch keine Themen vorhanden"
        description="Starte eine Recherche oder erstelle ein eigenes Thema."
      />
      <template v-else>
        <!-- Toolbar: bulk actions + filter -->
        <div class="mb-3 flex items-center justify-between">
          <div
            v-if="selectedTopicIds.size > 0"
            class="flex items-center gap-3"
          >
            <span class="text-sm font-medium text-go4-secondary dark:text-gray-100">
              {{ selectedTopicIds.size }} ausgewaehlt
            </span>
            <button
              class="rounded bg-red-600 px-3 py-1 text-xs font-medium text-white hover:bg-red-700"
              @click="handleBulkDeleteTopics"
            >
              Loeschen
            </button>
            <button
              class="text-xs text-go4-muted dark:text-gray-400 hover:text-go4-secondary dark:hover:text-gray-200"
              @click="selectedTopicIds = new Set()"
            >
              Auswahl aufheben
            </button>
          </div>
          <div v-else />
          <label
            class="flex items-center gap-2 text-xs text-go4-muted dark:text-gray-400 cursor-pointer select-none"
          >
            <input
              v-model="showAllTopics"
              type="checkbox"
              class="rounded border-gray-300 dark:border-gray-600 text-go4-primary focus:ring-go4-primary"
            >
            Alle anzeigen ({{ store.topics.length }})
          </label>
        </div>

        <EmptyState
          v-if="filteredTopics.length === 0"
          title="Keine aktiven Themen"
          description="Alle Themen wurden abgelehnt. Aktiviere 'Alle anzeigen' um sie zu sehen."
        />

        <div
          v-else
          class="overflow-hidden rounded-lg bg-white dark:bg-gray-800 shadow-sm"
        >
          <table class="w-full text-left text-sm">
            <thead
              class="border-b border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 text-xs uppercase tracking-wider text-go4-muted dark:text-gray-400"
            >
              <tr>
                <th class="w-10 px-4 py-3">
                  <input
                    type="checkbox"
                    class="rounded border-gray-300 dark:border-gray-600 text-go4-primary focus:ring-go4-primary"
                    :checked="
                      selectedTopicIds.size === filteredTopics.length && filteredTopics.length > 0
                    "
                    :indeterminate="
                      selectedTopicIds.size > 0 && selectedTopicIds.size < filteredTopics.length
                    "
                    @change="toggleAllTopics"
                  >
                </th>
                <th class="px-4 py-3 font-medium">
                  Thema
                </th>
                <th class="hidden px-4 py-3 font-medium md:table-cell">
                  Prioritaet
                </th>
                <th class="px-4 py-3 font-medium">
                  Status
                </th>
                <th class="px-4 py-3 text-right font-medium">
                  Aktionen
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-50 dark:divide-gray-700">
              <tr
                v-for="topic in filteredTopics"
                :key="topic.id"
                class="cursor-pointer transition hover:bg-gray-50/50 dark:hover:bg-gray-700/50"
                :class="
                  selectedTopicIds.has(topic.id) ? 'bg-go4-primary/5 dark:bg-go4-primary/10' : ''
                "
                @click="router.push(`/collector/topics/${topic.id}`)"
              >
                <td
                  class="w-10 px-4 py-3"
                  @click.stop
                >
                  <input
                    type="checkbox"
                    class="rounded border-gray-300 dark:border-gray-600 text-go4-primary focus:ring-go4-primary"
                    :checked="selectedTopicIds.has(topic.id)"
                    @change="toggleTopicSelect(topic.id)"
                  >
                </td>

                <!-- Thema -->
                <td class="px-4 py-3">
                  <div class="flex items-center gap-2">
                    <img
                      v-if="topic.image_url"
                      :src="topic.image_url"
                      alt=""
                      class="h-8 w-8 shrink-0 rounded object-cover"
                    >
                    <div class="min-w-0">
                      <p class="truncate font-medium text-go4-secondary dark:text-gray-100">
                        {{ topic.title }}
                      </p>
                      <p
                        v-if="topic.description"
                        class="mt-0.5 line-clamp-1 text-xs text-go4-muted dark:text-gray-400"
                      >
                        {{ topic.description }}
                      </p>
                    </div>
                  </div>
                </td>

                <!-- Prioritaet -->
                <td class="hidden px-4 py-3 md:table-cell">
                  <span class="text-xs text-go4-muted dark:text-gray-400">
                    {{ priorityLabels[topic.priority] || '-' }}
                  </span>
                </td>

                <!-- Status -->
                <td class="px-4 py-3">
                  <StatusBadge :status="topic.status" />
                </td>

                <!-- Aktionen -->
                <td
                  class="px-4 py-3"
                  @click.stop
                >
                  <div class="flex items-center justify-end gap-1.5">
                    <template v-if="topic.status === 'suggested'">
                      <button
                        class="rounded bg-green-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-green-700"
                        title="Genehmigen"
                        @click="handleApproveTopic(topic.id)"
                      >
                        Genehmigen
                      </button>
                      <button
                        class="rounded bg-red-100 dark:bg-red-900/20 px-2.5 py-1 text-xs font-medium text-red-700 dark:text-red-400 hover:bg-red-200"
                        title="Ablehnen"
                        @click="handleRejectTopic(topic.id)"
                      >
                        Ablehnen
                      </button>
                    </template>
                    <router-link
                      v-if="topic.content_piece_id"
                      :to="`/creator/${topic.content_piece_id}`"
                      class="rounded bg-blue-100 px-2.5 py-1 text-xs font-medium text-blue-700 hover:bg-blue-200"
                    >
                      Content
                    </router-link>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </div>

    <!-- ==================== Prompts Tab ==================== -->
    <div
      v-else-if="activeTab === 'prompts'"
      class="mt-6"
    >
      <!-- Loading -->
      <div
        v-if="promptsLoading"
        class="flex items-center justify-center py-12"
      >
        <span class="text-go4-muted dark:text-gray-400">Prompts laden...</span>
      </div>

      <!-- Error -->
      <div
        v-else-if="promptsError"
        class="rounded-lg bg-red-50 dark:bg-red-900/20 p-4 text-sm text-red-700 dark:text-red-400"
      >
        {{ promptsError }}
      </div>

      <!-- Prompt Cards -->
      <div
        v-else
        class="space-y-4"
      >
        <!-- Add prompt button -->
        <div class="flex justify-end">
          <button
            class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90"
            @click="openAddPromptModal"
          >
            + Prompt hinzufuegen
          </button>
        </div>

        <!-- No prompts -->
        <EmptyState
          v-if="
            promptsData.length === 0 &&
              (store.activeGroup?.analysis_prompt_slugs || []).length === 0
          "
          title="Keine Analyse-Prompts"
          description="Fuege einen Prompt hinzu, um Findings automatisch analysieren zu lassen."
        />

        <!-- Prompt cards -->
        <div
          v-for="prompt in promptsData"
          :key="prompt.slug"
          class="rounded-lg bg-white dark:bg-gray-800 shadow-sm"
        >
          <!-- Header -->
          <div
            class="flex items-center justify-between border-b border-gray-100 dark:border-gray-700 px-4 py-3"
          >
            <div class="min-w-0 flex-1">
              <h3 class="text-sm font-semibold text-go4-secondary dark:text-gray-100 truncate">
                {{ prompt.name }}
              </h3>
              <div class="mt-1 flex flex-wrap items-center gap-1.5">
                <span
                  class="inline-flex items-center rounded-full bg-blue-100 dark:bg-blue-900/30 px-2 py-0.5 text-xs font-medium text-blue-800 dark:text-blue-300"
                >
                  {{ prompt.provider }}
                </span>
                <span
                  class="inline-flex items-center rounded-full bg-purple-100 dark:bg-purple-900/30 px-2 py-0.5 text-xs font-medium text-purple-800 dark:text-purple-300"
                >
                  {{ prompt.model }}
                </span>
                <span
                  class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium"
                  :class="
                    prompt.processing_mode === 'each'
                      ? 'bg-teal-100 dark:bg-teal-900/30 text-teal-800 dark:text-teal-300'
                      : 'bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-300'
                  "
                >
                  {{ prompt.processing_mode === 'each' ? 'Pro Finding' : 'Alle Findings' }}
                </span>
                <span
                  class="inline-flex items-center rounded-full bg-gray-100 dark:bg-gray-700 px-2 py-0.5 text-xs font-medium text-gray-600 dark:text-gray-300"
                >
                  {{ prompt.slug }}
                </span>
              </div>
            </div>
            <div class="ml-3 flex shrink-0 items-center gap-2">
              <!-- Play button -->
              <button
                class="rounded-lg bg-green-600 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-green-700 disabled:opacity-50"
                :disabled="runningPromptSlug === prompt.slug || store.loading"
                @click="handleRunGroupPrompt(prompt.slug)"
              >
                {{ runningPromptSlug === prompt.slug ? 'Laeuft...' : 'Ausfuehren' }}
              </button>
              <!-- Edit link -->
              <router-link
                :to="`/settings/prompts/${prompt.id}`"
                class="rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-xs font-medium text-go4-secondary dark:text-gray-200 transition hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                Bearbeiten
              </router-link>
              <!-- Duplicate button -->
              <button
                class="rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-1.5 text-xs font-medium text-go4-secondary dark:text-gray-200 transition hover:bg-gray-50 dark:hover:bg-gray-700"
                @click="openDuplicatePromptModal(prompt.slug)"
              >
                Duplizieren
              </button>
              <!-- Remove button -->
              <button
                class="rounded-lg border border-red-300 dark:border-red-700 px-3 py-1.5 text-xs font-medium text-red-600 dark:text-red-400 transition hover:bg-red-50 dark:hover:bg-red-900/20"
                @click="handleRemovePrompt(prompt.slug)"
              >
                Entfernen
              </button>
            </div>
          </div>
          <!-- Body: System Prompt Preview -->
          <div class="px-4 py-3">
            <p
              class="line-clamp-3 whitespace-pre-wrap font-mono text-xs leading-relaxed text-go4-muted dark:text-gray-400"
            >
              {{ prompt.system_prompt }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- ==================== Findings Tab ==================== -->
    <div
      v-else-if="activeTab === 'findings'"
      class="mt-6"
    >
      <EmptyState
        v-if="store.findings.length === 0"
        title="Noch keine Findings vorhanden"
        description="Starte eine Recherche."
      />
      <template v-else>
        <!-- Toolbar: bulk actions + filter -->
        <div class="mb-3 flex items-center justify-between">
          <div
            v-if="selectedFindingIds.size > 0"
            class="flex items-center gap-3"
          >
            <span class="text-sm font-medium text-go4-secondary dark:text-gray-100">
              {{ selectedFindingIds.size }} ausgewaehlt
            </span>
            <button
              class="rounded bg-red-600 px-3 py-1 text-xs font-medium text-white hover:bg-red-700"
              @click="handleBulkDeleteFindings"
            >
              Loeschen
            </button>
            <button
              class="text-xs text-go4-muted dark:text-gray-400 hover:text-go4-secondary dark:hover:text-gray-200"
              @click="selectedFindingIds = new Set()"
            >
              Auswahl aufheben
            </button>
          </div>
          <div v-else />
          <label
            class="flex items-center gap-2 text-xs text-go4-muted dark:text-gray-400 cursor-pointer select-none"
          >
            <input
              v-model="showAllFindings"
              type="checkbox"
              class="rounded border-gray-300 dark:border-gray-600 text-go4-primary focus:ring-go4-primary"
            >
            Alle anzeigen ({{ store.findings.length }})
          </label>
        </div>

        <EmptyState
          v-if="filteredFindings.length === 0"
          title="Keine aktiven Findings"
          description="Alle Findings wurden verworfen. Aktiviere 'Alle anzeigen' um sie zu sehen."
        />

        <div
          v-else
          class="space-y-2"
        >
          <!-- Select all -->
          <div class="flex items-center gap-2 px-1">
            <input
              type="checkbox"
              class="rounded border-gray-300 dark:border-gray-600 text-go4-primary focus:ring-go4-primary"
              :checked="
                selectedFindingIds.size === filteredFindings.length && filteredFindings.length > 0
              "
              :indeterminate="
                selectedFindingIds.size > 0 && selectedFindingIds.size < filteredFindings.length
              "
              @change="toggleAllFindings"
            >
            <span class="text-xs text-go4-muted dark:text-gray-400">Alle auswaehlen</span>
          </div>

          <!-- Finding cards -->
          <div
            v-for="finding in filteredFindings"
            :key="finding.id"
            class="group flex items-start gap-3 rounded-lg bg-white dark:bg-gray-800 p-4 shadow-sm transition cursor-pointer hover:shadow-md"
            :class="selectedFindingIds.has(finding.id) ? 'ring-2 ring-go4-primary/30' : ''"
            @click="openFindingUrl(finding)"
          >
            <!-- Checkbox -->
            <div
              class="shrink-0 pt-0.5"
              @click.stop
            >
              <input
                type="checkbox"
                class="rounded border-gray-300 dark:border-gray-600 text-go4-primary focus:ring-go4-primary"
                :checked="selectedFindingIds.has(finding.id)"
                @change="toggleFindingSelect(finding.id)"
              >
            </div>

            <!-- Content -->
            <div class="min-w-0 flex-1">
              <!-- Title row with status + date -->
              <div class="flex items-start justify-between gap-2">
                <h4
                  class="text-sm font-medium text-go4-secondary dark:text-gray-100 line-clamp-1 group-hover:text-go4-primary"
                >
                  {{ finding.title }}
                </h4>
                <div class="flex shrink-0 items-center gap-2">
                  <StatusBadge :status="finding.status" />
                  <span class="whitespace-nowrap text-xs text-gray-400 dark:text-gray-500">
                    {{ formatDate(finding.found_at) }}
                  </span>
                </div>
              </div>
              <!-- Summary: max 2 lines -->
              <p
                v-if="finding.summary"
                class="mt-1 text-xs leading-relaxed text-go4-muted dark:text-gray-400 line-clamp-2"
              >
                {{ finding.summary }}
              </p>
            </div>

            <!-- Actions -->
            <div
              class="flex shrink-0 items-center gap-1"
              @click.stop
            >
              <button
                v-if="finding.status === 'new'"
                class="rounded px-2 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100 dark:text-blue-400 dark:hover:bg-blue-900/20"
                title="Als reviewed markieren"
                @click="handleReviewFinding(finding.id)"
              >
                Reviewed
              </button>
              <button
                v-if="finding.status !== 'dismissed'"
                class="rounded px-2 py-1 text-xs font-medium text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700"
                title="Verwerfen"
                @click="handleDismissFinding(finding.id)"
              >
                Verwerfen
              </button>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- ==================== Sources Tab ==================== -->
    <div
      v-else-if="activeTab === 'sources'"
      class="mt-6"
    >
      <div class="mb-4 flex justify-end">
        <router-link
          to="/collector/sources/new"
          class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90"
        >
          Quelle hinzufuegen
        </router-link>
      </div>
      <EmptyState
        v-if="store.sources.length === 0"
        title="Noch keine Quellen konfiguriert"
      />
      <div
        v-else
        class="overflow-hidden rounded-lg bg-white dark:bg-gray-800 shadow-sm"
      >
        <table class="w-full text-left text-sm">
          <thead
            class="border-b border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 text-xs uppercase tracking-wider text-go4-muted dark:text-gray-400"
          >
            <tr>
              <th class="px-4 py-3 font-medium">
                Name
              </th>
              <th class="px-4 py-3 font-medium">
                Typ
              </th>
              <th class="hidden px-4 py-3 font-medium lg:table-cell">
                Intervall
              </th>
              <th class="hidden px-4 py-3 font-medium lg:table-cell">
                Zuletzt
              </th>
              <th class="px-4 py-3 font-medium">
                Status
              </th>
              <th class="px-4 py-3 text-right font-medium">
                Aktionen
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50 dark:divide-gray-700">
            <tr
              v-for="source in store.sources"
              :key="source.id"
              class="cursor-pointer transition hover:bg-gray-50/50 dark:hover:bg-gray-700/50"
              @click="router.push(`/collector/sources/${source.id}`)"
            >
              <!-- Name + URL -->
              <td class="px-4 py-3">
                <div class="min-w-0">
                  <p class="truncate font-medium text-go4-secondary dark:text-gray-100">
                    {{ source.name }}
                  </p>
                  <p class="mt-0.5 max-w-xs truncate text-xs text-go4-muted dark:text-gray-400">
                    {{ source.url }}
                  </p>
                </div>
              </td>

              <!-- Typ -->
              <td class="px-4 py-3">
                <span
                  class="inline-block rounded-full px-2 py-0.5 text-xs font-medium"
                  :class="
                    sourceTypeBadge[source.source_type] ||
                      'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200'
                  "
                >
                  {{ source.source_type }}
                </span>
              </td>

              <!-- Intervall -->
              <td
                class="hidden whitespace-nowrap px-4 py-3 text-xs text-go4-muted dark:text-gray-400 lg:table-cell"
              >
                {{ source.fetch_interval_hours }}h
              </td>

              <!-- Zuletzt -->
              <td
                class="hidden whitespace-nowrap px-4 py-3 text-xs text-gray-400 dark:text-gray-500 lg:table-cell"
              >
                {{ source.last_fetched_at ? formatDate(source.last_fetched_at) : '-' }}
              </td>

              <!-- Status -->
              <td class="px-4 py-3">
                <button
                  class="rounded-full px-2.5 py-0.5 text-xs font-medium transition"
                  :class="
                    source.active
                      ? 'bg-green-100 text-green-700 hover:bg-green-200'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600'
                  "
                  @click.stop="handleToggleSource(source)"
                >
                  {{ source.active ? 'Aktiv' : 'Inaktiv' }}
                </button>
              </td>

              <!-- Aktionen -->
              <td class="px-4 py-3">
                <div class="flex items-center justify-end">
                  <button
                    class="rounded-full p-1.5 text-go4-primary hover:bg-go4-primary/10 disabled:opacity-50"
                    :disabled="store.loading"
                    title="Quelle durchsuchen"
                    @click.stop="handleRunCollector(source.id)"
                  >
                    <svg
                      class="h-4 w-4"
                      fill="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path d="M8 5v14l11-7z" />
                    </svg>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ==================== Group Modal ==================== -->
    <div
      v-if="showGroupModal"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/70"
      @click.self="showGroupModal = false"
    >
      <div class="w-full max-w-md rounded-lg bg-white dark:bg-gray-800 p-6 shadow-xl">
        <h3 class="text-lg font-semibold text-go4-secondary dark:text-gray-100">
          {{ editingGroup ? 'Gruppe bearbeiten' : 'Neue Gruppe' }}
        </h3>

        <div
          v-if="groupError"
          class="mt-3 rounded-lg bg-red-50 dark:bg-red-900/20 p-3 text-sm text-red-700 dark:text-red-400"
        >
          {{ groupError }}
        </div>

        <form
          class="mt-4 space-y-4"
          @submit.prevent="handleGroupSubmit"
        >
          <div>
            <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">Name</label>
            <input
              v-model="groupForm.name"
              type="text"
              required
              class="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm dark:bg-gray-700 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
              placeholder="z.B. Wettbewerber Monitoring"
              @input="generateSlug"
            >
          </div>

          <div v-if="!editingGroup">
            <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">Slug</label>
            <input
              v-model="groupForm.slug"
              type="text"
              required
              pattern="^[a-z0-9-]+$"
              class="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm dark:bg-gray-700 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
              placeholder="wettbewerber-monitoring"
            >
            <p class="mt-1 text-xs text-go4-muted dark:text-gray-400">
              Nur Kleinbuchstaben, Zahlen und Bindestriche
            </p>
          </div>

          <div>
            <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">Beschreibung</label>
            <textarea
              v-model="groupForm.description"
              rows="2"
              class="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm dark:bg-gray-700 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
              placeholder="Wofuer ist diese Gruppe?"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">
              Fetch-Intervall (Stunden)
            </label>
            <input
              v-model.number="groupForm.fetch_interval_hours"
              type="number"
              min="1"
              max="168"
              class="mt-1 block w-32 rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm dark:bg-gray-700 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
            >
          </div>

          <div class="flex justify-end gap-3 pt-2">
            <button
              type="button"
              class="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm font-medium text-go4-secondary dark:text-gray-100 hover:bg-gray-50 dark:hover:bg-gray-700"
              @click="showGroupModal = false"
            >
              Abbrechen
            </button>
            <button
              type="submit"
              :disabled="groupSaving"
              class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary/90 disabled:opacity-50"
            >
              {{ groupSaving ? 'Speichern...' : 'Speichern' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- ==================== Add Prompt Modal ==================== -->
    <div
      v-if="showAddPromptModal"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/70"
      @click.self="showAddPromptModal = false"
    >
      <div class="w-full max-w-md rounded-lg bg-white dark:bg-gray-800 p-6 shadow-xl">
        <h3 class="text-lg font-semibold text-go4-secondary dark:text-gray-100">
          {{ duplicateSourceSlug ? 'Prompt duplizieren' : 'Prompt hinzufuegen' }}
        </h3>
        <p
          v-if="duplicateSourceSlug"
          class="mt-1 text-xs text-go4-muted dark:text-gray-400"
        >
          Vorlage: <span class="font-mono">{{ duplicateSourceSlug }}</span>
        </p>

        <div
          v-if="addPromptError"
          class="mt-3 rounded-lg bg-red-50 dark:bg-red-900/20 p-3 text-sm text-red-700 dark:text-red-400"
        >
          {{ addPromptError }}
        </div>

        <form
          class="mt-4 space-y-4"
          @submit.prevent="handleAddPrompt"
        >
          <div>
            <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">
              Zweck
            </label>
            <input
              v-model="addPromptForm.purpose"
              type="text"
              required
              pattern="^[a-z0-9-]+$"
              class="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm dark:bg-gray-700 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
              placeholder="z.B. social, briefing, newsletter"
            >
            <p class="mt-1 text-xs text-go4-muted dark:text-gray-400">
              Nur Kleinbuchstaben, Zahlen und Bindestriche
            </p>
          </div>

          <div v-if="addPromptSlugPreview">
            <label class="block text-xs font-medium text-go4-muted dark:text-gray-400">
              Slug wird:
            </label>
            <p class="mt-0.5 font-mono text-sm text-go4-secondary dark:text-gray-200">
              {{ addPromptSlugPreview }}
            </p>
          </div>

          <p class="text-xs text-go4-muted dark:text-gray-400">
            {{
              duplicateSourceSlug
                ? `Der Prompt wird von "${duplicateSourceSlug}" dupliziert.`
                : 'Der Prompt wird vom ersten bestehenden Prompt der Gruppe dupliziert.'
            }}
          </p>

          <div class="flex justify-end gap-3 pt-2">
            <button
              type="button"
              class="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm font-medium text-go4-secondary dark:text-gray-100 hover:bg-gray-50 dark:hover:bg-gray-700"
              @click="showAddPromptModal = false"
            >
              Abbrechen
            </button>
            <button
              type="submit"
              :disabled="addPromptSaving || !addPromptForm.purpose"
              class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary/90 disabled:opacity-50"
            >
              {{ addPromptSaving ? 'Erstellen...' : 'Erstellen' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>
