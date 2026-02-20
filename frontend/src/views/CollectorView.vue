<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCollectorStore } from '@/stores/collector'
import PageHeader from '@/components/ui/PageHeader.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import EmptyState from '@/components/ui/EmptyState.vue'

const router = useRouter()
const store = useCollectorStore()

const activeTab = ref('topics')
const generating = ref(null)
const generatePlatform = ref('facebook')
const generateType = ref('post')
const showGenerateModal = ref(false)
const selectedTopicId = ref(null)

const tabs = [
  { key: 'topics', label: 'Themen' },
  { key: 'findings', label: 'Findings' },
  { key: 'sources', label: 'Quellen' }
]

const sourceTypeBadge = {
  rss: 'bg-orange-100 text-orange-800',
  website: 'bg-blue-100 text-blue-800',
  websearch: 'bg-purple-100 text-purple-800',
  inbox: 'bg-green-100 text-green-800'
}

const priorityLabels = ['', 'Sehr hoch', 'Hoch', 'Normal', 'Niedrig', 'Sehr niedrig']

onMounted(async () => {
  await Promise.all([store.fetchSources(), store.fetchFindings(), store.fetchTopics()])
})

async function handleRunCollector(sourceId = null) {
  await store.triggerCollector(sourceId)
}

async function handleApproveTopic(topicId) {
  await store.editTopic(topicId, { status: 'approved' })
}

async function handleRejectTopic(topicId) {
  await store.editTopic(topicId, { status: 'rejected' })
}

function openGenerateModal(topicId) {
  selectedTopicId.value = topicId
  generatePlatform.value = 'facebook'
  generateType.value = 'post'
  showGenerateModal.value = true
}

async function handleGenerate() {
  generating.value = selectedTopicId.value
  showGenerateModal.value = false
  try {
    await store.generateContent(selectedTopicId.value, generatePlatform.value, generateType.value)
  } finally {
    generating.value = null
  }
}

async function handleDismissFinding(findingId) {
  await store.changeFindingStatus(findingId, 'dismissed')
}

async function handleReviewFinding(findingId) {
  await store.changeFindingStatus(findingId, 'reviewed')
}

async function handleDeleteSource(sourceId) {
  await store.removeSource(sourceId)
}

async function handleToggleSource(source) {
  await store.editSource(source.id, { active: !source.active })
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
    <PageHeader title="Collector" subtitle="Quellen scannen, Findings sammeln, Topics generieren">
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
        <button class="font-medium underline" @click="activeTab = 'sources'">Quellen</button>
        eine RSS-, Website- oder Websearch-Quelle an.
      </template>
      <template v-else>
        Collector abgeschlossen: {{ store.runResult.findings_count }} neue Findings,
        {{ store.runResult.suggestions_count }} Topic-Vorschlaege
        <span v-if="store.runResult.errors.length > 0" class="ml-2 text-red-600">
          ({{ store.runResult.errors.length }} Fehler)
        </span>
      </template>
    </div>

    <!-- Error -->
    <div v-if="store.error" class="mt-4 rounded-lg bg-red-50 p-4 text-sm text-red-700">
      {{ store.error }}
    </div>

    <!-- Tabs -->
    <div class="mt-6 border-b border-gray-200">
      <nav class="-mb-px flex space-x-8">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="border-b-2 px-1 pb-3 text-sm font-medium transition"
          :class="
            activeTab === tab.key
              ? 'border-go4-primary text-go4-primary'
              : 'border-transparent text-go4-muted hover:border-gray-300 hover:text-go4-secondary'
          "
          @click="activeTab = tab.key"
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
            class="ml-1.5 rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600"
          >
            {{ store.newFindings.length }}
          </span>
          <span
            v-if="tab.key === 'sources'"
            class="ml-1.5 rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600"
          >
            {{ store.sources.length }}
          </span>
        </button>
      </nav>
    </div>

    <!-- Loading -->
    <div v-if="store.loading" class="mt-8 flex items-center justify-center py-12">
      <span class="text-go4-muted">Laden...</span>
    </div>

    <!-- ==================== Topics Tab ==================== -->
    <div v-else-if="activeTab === 'topics'" class="mt-6">
      <EmptyState
        v-if="store.topics.length === 0"
        title="Noch keine Themen vorhanden"
        description="Starte eine Recherche oder erstelle ein eigenes Thema."
      />
      <div v-else class="overflow-hidden rounded-lg bg-white shadow-sm">
        <table class="w-full text-left text-sm">
          <thead
            class="border-b border-gray-100 bg-gray-50 text-xs uppercase tracking-wider text-go4-muted"
          >
            <tr>
              <th class="px-4 py-3 font-medium">Thema</th>
              <th class="hidden px-4 py-3 font-medium md:table-cell">Prioritaet</th>
              <th class="hidden px-4 py-3 font-medium lg:table-cell">Plattformen</th>
              <th class="px-4 py-3 font-medium">Status</th>
              <th class="px-4 py-3 text-right font-medium">Aktionen</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50">
            <tr
              v-for="topic in store.topics"
              :key="topic.id"
              class="transition hover:bg-gray-50/50"
            >
              <!-- Thema -->
              <td class="px-4 py-3">
                <div class="flex items-center gap-2">
                  <img
                    v-if="topic.image_url"
                    :src="topic.image_url"
                    alt=""
                    class="h-8 w-8 shrink-0 rounded object-cover"
                  />
                  <div class="min-w-0">
                    <p class="truncate font-medium text-go4-secondary">
                      {{ topic.title }}
                    </p>
                    <p v-if="topic.description" class="mt-0.5 line-clamp-1 text-xs text-go4-muted">
                      {{ topic.description }}
                    </p>
                  </div>
                </div>
              </td>

              <!-- Prioritaet -->
              <td class="hidden px-4 py-3 md:table-cell">
                <span class="text-xs text-go4-muted">
                  {{ priorityLabels[topic.priority] || '-' }}
                </span>
              </td>

              <!-- Plattformen -->
              <td class="hidden px-4 py-3 lg:table-cell">
                <div class="flex flex-wrap gap-1">
                  <span
                    v-if="topic.source_type === 'manual'"
                    class="rounded-full bg-indigo-100 px-2 py-0.5 text-xs text-indigo-700"
                  >
                    Eigenes Thema
                  </span>
                  <span
                    v-for="p in topic.platforms || []"
                    :key="p"
                    class="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600"
                  >
                    {{ p }}
                  </span>
                </div>
              </td>

              <!-- Status -->
              <td class="px-4 py-3">
                <StatusBadge :status="topic.status" />
              </td>

              <!-- Aktionen -->
              <td class="px-4 py-3">
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
                      class="rounded bg-red-100 px-2.5 py-1 text-xs font-medium text-red-700 hover:bg-red-200"
                      title="Ablehnen"
                      @click="handleRejectTopic(topic.id)"
                    >
                      Ablehnen
                    </button>
                  </template>
                  <button
                    v-if="topic.status === 'approved' || topic.status === 'suggested'"
                    class="rounded bg-go4-primary px-2.5 py-1 text-xs font-medium text-white hover:bg-go4-primary/90 disabled:opacity-50"
                    :disabled="generating === topic.id"
                    @click="openGenerateModal(topic.id)"
                  >
                    {{ generating === topic.id ? 'Generiert...' : 'Generieren' }}
                  </button>
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
    </div>

    <!-- ==================== Findings Tab ==================== -->
    <div v-else-if="activeTab === 'findings'" class="mt-6">
      <EmptyState
        v-if="store.findings.length === 0"
        title="Noch keine Findings vorhanden"
        description="Starte eine Recherche."
      />
      <div v-else class="overflow-hidden rounded-lg bg-white shadow-sm">
        <table class="w-full text-left text-sm">
          <thead
            class="border-b border-gray-100 bg-gray-50 text-xs uppercase tracking-wider text-go4-muted"
          >
            <tr>
              <th class="px-4 py-3 font-medium">Titel</th>
              <th class="hidden px-4 py-3 font-medium lg:table-cell">Gefunden</th>
              <th class="px-4 py-3 font-medium">Status</th>
              <th class="px-4 py-3 text-right font-medium">Aktionen</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50">
            <tr
              v-for="finding in store.findings"
              :key="finding.id"
              class="transition hover:bg-gray-50/50"
            >
              <td class="px-4 py-3">
                <div class="min-w-0">
                  <a
                    :href="finding.url"
                    target="_blank"
                    class="truncate font-medium text-go4-secondary hover:text-go4-primary"
                  >
                    {{ finding.title }}
                  </a>
                  <p v-if="finding.summary" class="mt-0.5 line-clamp-1 text-xs text-go4-muted">
                    {{ finding.summary }}
                  </p>
                </div>
              </td>
              <td class="hidden whitespace-nowrap px-4 py-3 text-xs text-gray-400 lg:table-cell">
                {{ formatDate(finding.found_at) }}
              </td>
              <td class="px-4 py-3">
                <StatusBadge :status="finding.status" />
              </td>
              <td class="px-4 py-3">
                <div class="flex items-center justify-end gap-1.5">
                  <button
                    v-if="finding.status === 'new'"
                    class="rounded bg-blue-100 px-2.5 py-1 text-xs font-medium text-blue-700 hover:bg-blue-200"
                    @click="handleReviewFinding(finding.id)"
                  >
                    Reviewed
                  </button>
                  <button
                    v-if="finding.status !== 'dismissed'"
                    class="rounded bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600 hover:bg-gray-200"
                    @click="handleDismissFinding(finding.id)"
                  >
                    Verwerfen
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ==================== Sources Tab ==================== -->
    <div v-else-if="activeTab === 'sources'" class="mt-6">
      <div class="mb-4 flex justify-end">
        <router-link
          to="/collector/sources/new"
          class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90"
        >
          Quelle hinzufuegen
        </router-link>
      </div>
      <EmptyState v-if="store.sources.length === 0" title="Noch keine Quellen konfiguriert" />
      <div v-else class="overflow-hidden rounded-lg bg-white shadow-sm">
        <table class="w-full text-left text-sm">
          <thead
            class="border-b border-gray-100 bg-gray-50 text-xs uppercase tracking-wider text-go4-muted"
          >
            <tr>
              <th class="px-4 py-3 font-medium">Name</th>
              <th class="px-4 py-3 font-medium">Typ</th>
              <th class="hidden px-4 py-3 font-medium md:table-cell">Keywords</th>
              <th class="hidden px-4 py-3 font-medium lg:table-cell">Intervall</th>
              <th class="hidden px-4 py-3 font-medium lg:table-cell">Zuletzt</th>
              <th class="px-4 py-3 font-medium">Status</th>
              <th class="px-4 py-3 text-right font-medium">Aktionen</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50">
            <tr
              v-for="source in store.sources"
              :key="source.id"
              class="transition hover:bg-gray-50/50"
            >
              <!-- Name + URL -->
              <td class="px-4 py-3">
                <div class="min-w-0">
                  <p class="truncate font-medium text-go4-secondary">
                    {{ source.name }}
                  </p>
                  <p class="mt-0.5 max-w-xs truncate text-xs text-go4-muted">
                    {{ source.url }}
                  </p>
                </div>
              </td>

              <!-- Typ -->
              <td class="px-4 py-3">
                <span
                  class="inline-block rounded-full px-2 py-0.5 text-xs font-medium"
                  :class="sourceTypeBadge[source.source_type] || 'bg-gray-100 text-gray-800'"
                >
                  {{ source.source_type }}
                </span>
              </td>

              <!-- Keywords -->
              <td class="hidden px-4 py-3 md:table-cell">
                <div class="flex max-w-xs flex-wrap gap-1">
                  <span
                    v-for="kw in (source.keywords || []).slice(0, 3)"
                    :key="kw"
                    class="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600"
                  >
                    {{ kw }}
                  </span>
                  <span v-if="(source.keywords || []).length > 3" class="text-xs text-gray-400">
                    +{{ source.keywords.length - 3 }}
                  </span>
                </div>
              </td>

              <!-- Intervall -->
              <td class="hidden whitespace-nowrap px-4 py-3 text-xs text-go4-muted lg:table-cell">
                {{ source.fetch_interval_hours }}h
              </td>

              <!-- Zuletzt -->
              <td class="hidden whitespace-nowrap px-4 py-3 text-xs text-gray-400 lg:table-cell">
                {{ source.last_fetched_at ? formatDate(source.last_fetched_at) : '-' }}
              </td>

              <!-- Status -->
              <td class="px-4 py-3">
                <button
                  class="rounded-full px-2.5 py-0.5 text-xs font-medium transition"
                  :class="
                    source.active
                      ? 'bg-green-100 text-green-700 hover:bg-green-200'
                      : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                  "
                  @click="handleToggleSource(source)"
                >
                  {{ source.active ? 'Aktiv' : 'Inaktiv' }}
                </button>
              </td>

              <!-- Aktionen -->
              <td class="px-4 py-3">
                <div class="flex items-center justify-end gap-1.5">
                  <button
                    class="rounded bg-go4-primary/10 px-2.5 py-1 text-xs font-medium text-go4-primary hover:bg-go4-primary/20"
                    :disabled="store.loading"
                    @click="handleRunCollector(source.id)"
                  >
                    Suchen
                  </button>
                  <router-link
                    :to="`/collector/sources/${source.id}`"
                    class="rounded bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600 hover:bg-gray-200"
                  >
                    Bearbeiten
                  </router-link>
                  <button
                    class="rounded bg-red-100 px-2.5 py-1 text-xs font-medium text-red-700 hover:bg-red-200"
                    @click="handleDeleteSource(source.id)"
                  >
                    Loeschen
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Generate Modal -->
    <div
      v-if="showGenerateModal"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      @click.self="showGenerateModal = false"
    >
      <div class="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <h3 class="text-lg font-semibold text-go4-secondary">Content generieren</h3>
        <div class="mt-4 space-y-4">
          <div>
            <label class="block text-sm font-medium text-go4-secondary">Plattform</label>
            <select
              v-model="generatePlatform"
              class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="facebook">Facebook</option>
              <option value="instagram">Instagram</option>
              <option value="linkedin">LinkedIn</option>
              <option value="email">E-Mail</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-go4-secondary">Content-Typ</label>
            <select
              v-model="generateType"
              class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="post">Post</option>
              <option value="story">Story</option>
              <option value="reel">Reel</option>
              <option value="email">E-Mail</option>
            </select>
          </div>
        </div>
        <div class="mt-6 flex justify-end gap-3">
          <button
            class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-go4-secondary hover:bg-gray-50"
            @click="showGenerateModal = false"
          >
            Abbrechen
          </button>
          <button
            class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary/90"
            @click="handleGenerate"
          >
            Generieren
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
