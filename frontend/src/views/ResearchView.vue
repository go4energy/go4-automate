<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useResearchStore } from '@/stores/research'

const router = useRouter()
const store = useResearchStore()

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
  websearch: 'bg-purple-100 text-purple-800'
}

const statusBadge = {
  suggested: 'bg-yellow-100 text-yellow-800',
  approved: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
  generating: 'bg-blue-100 text-blue-800',
  generated: 'bg-emerald-100 text-emerald-800',
  new: 'bg-gray-100 text-gray-800',
  reviewed: 'bg-blue-100 text-blue-800',
  used: 'bg-green-100 text-green-800',
  dismissed: 'bg-red-100 text-red-800'
}

const priorityLabels = ['', 'Sehr hoch', 'Hoch', 'Normal', 'Niedrig', 'Sehr niedrig']

onMounted(async () => {
  await Promise.all([store.fetchSources(), store.fetchFindings(), store.fetchTopics()])
})

async function handleRunResearch(sourceId = null) {
  await store.triggerResearch(sourceId)
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
  <div class="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-go4-secondary">Research Agent</h1>
        <p class="mt-1 text-go4-muted">Themen entdecken, analysieren und Content generieren</p>
      </div>
      <div class="flex gap-3">
        <button
          class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90 disabled:opacity-50"
          :disabled="store.loading"
          @click="handleRunResearch()"
        >
          {{ store.loading ? 'Suche läuft...' : 'Research starten' }}
        </button>
        <router-link
          to="/research/topics/new"
          class="rounded-lg border border-go4-primary px-4 py-2 text-sm font-medium text-go4-primary transition hover:bg-go4-primary/5"
        >
          Eigenes Thema
        </router-link>
      </div>
    </div>

    <!-- Run Result -->
    <div v-if="store.runResult" class="mt-4 rounded-lg bg-green-50 p-4 text-sm text-green-800">
      Research abgeschlossen: {{ store.runResult.findings_count }} neue Findings,
      {{ store.runResult.suggestions_count }} Topic-Vorschläge
      <span v-if="store.runResult.errors.length > 0" class="ml-2 text-red-600">
        ({{ store.runResult.errors.length }} Fehler)
      </span>
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

    <!-- Topics Tab -->
    <div v-else-if="activeTab === 'topics'" class="mt-6">
      <div v-if="store.topics.length === 0" class="py-12 text-center text-go4-muted">
        Noch keine Themen vorhanden. Starte eine Recherche oder erstelle ein eigenes Thema.
      </div>
      <div v-else class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        <div
          v-for="topic in store.topics"
          :key="topic.id"
          class="rounded-lg bg-white p-5 shadow-sm"
        >
          <div class="flex items-start justify-between">
            <h3 class="font-medium text-go4-secondary">{{ topic.title }}</h3>
            <span
              class="ml-2 shrink-0 rounded-full px-2 py-0.5 text-xs font-medium"
              :class="statusBadge[topic.status] || 'bg-gray-100 text-gray-800'"
            >
              {{ topic.status }}
            </span>
          </div>
          <p class="mt-2 line-clamp-3 text-sm text-go4-muted">{{ topic.description }}</p>
          <div class="mt-3 flex flex-wrap items-center gap-2">
            <span class="text-xs text-go4-muted">{{ priorityLabels[topic.priority] }}</span>
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
          <div v-if="topic.image_url" class="mt-3">
            <img :src="topic.image_url" alt="Topic Bild" class="h-24 w-full rounded object-cover" />
          </div>
          <div class="mt-4 flex gap-2">
            <template v-if="topic.status === 'suggested'">
              <button
                class="rounded bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700"
                @click="handleApproveTopic(topic.id)"
              >
                Genehmigen
              </button>
              <button
                class="rounded bg-red-100 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-200"
                @click="handleRejectTopic(topic.id)"
              >
                Ablehnen
              </button>
            </template>
            <template v-if="topic.status === 'approved' || topic.status === 'suggested'">
              <button
                class="rounded bg-go4-primary px-3 py-1.5 text-xs font-medium text-white hover:bg-go4-primary/90 disabled:opacity-50"
                :disabled="generating === topic.id"
                @click="openGenerateModal(topic.id)"
              >
                {{ generating === topic.id ? 'Generiert...' : 'Content generieren' }}
              </button>
            </template>
            <router-link
              v-if="topic.content_piece_id"
              :to="`/content/${topic.content_piece_id}`"
              class="rounded bg-blue-100 px-3 py-1.5 text-xs font-medium text-blue-700 hover:bg-blue-200"
            >
              Content ansehen
            </router-link>
          </div>
        </div>
      </div>
    </div>

    <!-- Findings Tab -->
    <div v-else-if="activeTab === 'findings'" class="mt-6">
      <div v-if="store.findings.length === 0" class="py-12 text-center text-go4-muted">
        Noch keine Findings vorhanden. Starte eine Recherche.
      </div>
      <div v-else class="space-y-3">
        <div
          v-for="finding in store.findings"
          :key="finding.id"
          class="flex items-center justify-between rounded-lg bg-white p-4 shadow-sm"
        >
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2">
              <a
                :href="finding.url"
                target="_blank"
                class="truncate font-medium text-go4-secondary hover:text-go4-primary"
              >
                {{ finding.title }}
              </a>
              <span
                class="shrink-0 rounded-full px-2 py-0.5 text-xs font-medium"
                :class="statusBadge[finding.status] || 'bg-gray-100 text-gray-800'"
              >
                {{ finding.status }}
              </span>
            </div>
            <p v-if="finding.summary" class="mt-1 line-clamp-1 text-sm text-go4-muted">
              {{ finding.summary }}
            </p>
            <p class="mt-1 text-xs text-gray-400">{{ formatDate(finding.found_at) }}</p>
          </div>
          <div class="ml-4 flex shrink-0 gap-2">
            <button
              v-if="finding.status === 'new'"
              class="rounded bg-blue-100 px-3 py-1.5 text-xs font-medium text-blue-700 hover:bg-blue-200"
              @click="handleReviewFinding(finding.id)"
            >
              Reviewed
            </button>
            <button
              v-if="finding.status !== 'dismissed'"
              class="rounded bg-gray-100 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-200"
              @click="handleDismissFinding(finding.id)"
            >
              Verwerfen
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Sources Tab -->
    <div v-else-if="activeTab === 'sources'" class="mt-6">
      <div class="mb-4 flex justify-end">
        <router-link
          to="/research/sources/new"
          class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90"
        >
          Quelle hinzufügen
        </router-link>
      </div>
      <div v-if="store.sources.length === 0" class="py-12 text-center text-go4-muted">
        Noch keine Quellen konfiguriert.
      </div>
      <div v-else class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        <div
          v-for="source in store.sources"
          :key="source.id"
          class="rounded-lg bg-white p-5 shadow-sm"
        >
          <div class="flex items-start justify-between">
            <h3 class="font-medium text-go4-secondary">{{ source.name }}</h3>
            <span
              class="ml-2 shrink-0 rounded-full px-2 py-0.5 text-xs font-medium"
              :class="sourceTypeBadge[source.source_type] || 'bg-gray-100 text-gray-800'"
            >
              {{ source.source_type }}
            </span>
          </div>
          <p class="mt-1 truncate text-sm text-go4-muted">{{ source.url }}</p>
          <div class="mt-2 flex flex-wrap gap-1">
            <span
              v-for="kw in source.keywords || []"
              :key="kw"
              class="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600"
            >
              {{ kw }}
            </span>
          </div>
          <p class="mt-2 text-xs text-gray-400">
            Intervall: {{ source.fetch_interval_hours }}h
            <span v-if="source.last_fetched_at">
              | Zuletzt: {{ formatDate(source.last_fetched_at) }}
            </span>
          </p>
          <div class="mt-4 flex items-center justify-between">
            <button
              class="text-sm"
              :class="source.active ? 'text-green-600' : 'text-gray-400'"
              @click="handleToggleSource(source)"
            >
              {{ source.active ? 'Aktiv' : 'Inaktiv' }}
            </button>
            <div class="flex gap-2">
              <button
                class="rounded bg-go4-primary/10 px-3 py-1.5 text-xs font-medium text-go4-primary hover:bg-go4-primary/20"
                :disabled="store.loading"
                @click="handleRunResearch(source.id)"
              >
                Jetzt suchen
              </button>
              <router-link
                :to="`/research/sources/${source.id}`"
                class="rounded bg-gray-100 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-200"
              >
                Bearbeiten
              </router-link>
              <button
                class="rounded bg-red-100 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-200"
                @click="handleDeleteSource(source.id)"
              >
                Löschen
              </button>
            </div>
          </div>
        </div>
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
