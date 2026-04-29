<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCreatorStore } from '@/stores/creator'
import ContentCard from '@/components/ContentCard.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import StatCard from '@/components/ui/StatCard.vue'
import EmptyState from '@/components/ui/EmptyState.vue'

const router = useRouter()
const store = useCreatorStore()

const statusFilter = ref('')
const platformFilter = ref('')
const showGenerateForm = ref(false)
const generateLoading = ref(false)

const generateForm = ref({
  topic: '',
  platform: 'facebook',
  content_type: 'post'
})

async function loadPieces() {
  const params = {}
  if (statusFilter.value) params.status = statusFilter.value
  if (platformFilter.value) params.platform = platformFilter.value
  await store.fetchPieces(params)
}

async function handleGenerate() {
  if (!generateForm.value.topic) return
  generateLoading.value = true
  try {
    const piece = await store.generate(generateForm.value)
    showGenerateForm.value = false
    generateForm.value = { topic: '', platform: 'facebook', content_type: 'post' }
    router.push(`/creator/${piece.id}`)
  } catch {
    // error is set in store
  } finally {
    generateLoading.value = false
  }
}

function handleEdit(piece) {
  router.push(`/creator/${piece.id}`)
}

async function handleApprove(piece) {
  const scheduledAt = new Date()
  scheduledAt.setDate(scheduledAt.getDate() + 1)
  scheduledAt.setHours(9, 0, 0, 0)
  try {
    await store.approve(piece.id, {
      approved_by: 'dashboard',
      scheduled_at: scheduledAt.toISOString()
    })
  } catch {
    // error is set in store
  }
}

async function handlePublish(piece) {
  try {
    await store.publish(piece.id)
    await loadPieces()
  } catch {
    // error is set in store
  }
}

async function handleDelete(piece) {
  if (!confirm(`"${piece.title}" wirklich l\u00f6schen?`)) return
  try {
    await store.remove(piece.id)
  } catch {
    // error is set in store
  }
}

onMounted(() => {
  loadPieces()
})
</script>

<template>
  <div>
    <PageHeader
      title="Creator"
    >
      <template #actions>
        <button
          class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark"
          @click="showGenerateForm = !showGenerateForm"
        >
          Post generieren
        </button>
      </template>
    </PageHeader>

    <!-- Stats Bar -->
    <div class="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
      <StatCard
        label="Entwuerfe"
        :value="store.stats.draft"
        color="text-yellow-600"
      />
      <StatCard
        label="Geplant"
        :value="store.stats.scheduled"
        color="text-blue-600"
      />
      <StatCard
        label="Veroeffentlicht"
        :value="store.stats.published"
        color="text-green-600"
      />
      <StatCard
        label="Fehlgeschlagen"
        :value="store.stats.failed"
        color="text-red-600"
      />
    </div>

    <!-- Generate Form -->
    <div
      v-if="showGenerateForm"
      class="mt-6 rounded-lg bg-white dark:bg-gray-800 p-6 shadow-sm"
    >
      <h2 class="text-sm font-semibold text-go4-secondary dark:text-gray-100">
        Neuen Post generieren
      </h2>
      <div class="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div>
          <label class="block text-xs font-medium text-go4-muted dark:text-gray-400">Thema</label>
          <input
            v-model="generateForm.topic"
            type="text"
            placeholder="z.B. Energieeffizienz im Buero"
            class="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
          >
        </div>
        <div>
          <label class="block text-xs font-medium text-go4-muted dark:text-gray-400">Plattform</label>
          <select
            v-model="generateForm.platform"
            class="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
          >
            <option value="facebook">
              Facebook
            </option>
            <option value="instagram">
              Instagram
            </option>
            <option value="linkedin">
              LinkedIn
            </option>
          </select>
        </div>
        <div>
          <label class="block text-xs font-medium text-go4-muted dark:text-gray-400">Content-Typ</label>
          <select
            v-model="generateForm.content_type"
            class="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
          >
            <option value="post">
              Post
            </option>
            <option value="story">
              Story
            </option>
            <option value="reel">
              Reel
            </option>
            <option value="carousel">
              Carousel
            </option>
          </select>
        </div>
      </div>
      <div class="mt-4 flex items-center gap-3">
        <button
          :disabled="generateLoading || !generateForm.topic"
          class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark disabled:opacity-50"
          @click="handleGenerate"
        >
          {{ generateLoading ? 'Generiert...' : 'Generieren' }}
        </button>
        <button
          class="rounded-lg bg-go4-surface px-4 py-2 text-sm font-medium text-go4-secondary dark:text-gray-100 hover:bg-gray-200 dark:hover:bg-gray-600"
          @click="showGenerateForm = false"
        >
          Abbrechen
        </button>
      </div>
      <p
        v-if="store.error"
        class="mt-2 text-sm text-red-600 dark:text-red-400"
      >
        {{ store.error }}
      </p>
    </div>

    <!-- Filters -->
    <div class="mt-6 flex items-center gap-4">
      <select
        v-model="statusFilter"
        class="rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
        @change="loadPieces"
      >
        <option value="">
          Alle Status
        </option>
        <option value="draft">
          Entwurf
        </option>
        <option value="scheduled">
          Geplant
        </option>
        <option value="published">
          Veroeffentlicht
        </option>
        <option value="failed">
          Fehlgeschlagen
        </option>
      </select>
      <select
        v-model="platformFilter"
        class="rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
        @change="loadPieces"
      >
        <option value="">
          Alle Plattformen
        </option>
        <option value="facebook">
          Facebook
        </option>
        <option value="instagram">
          Instagram
        </option>
        <option value="linkedin">
          LinkedIn
        </option>
      </select>
    </div>

    <!-- Loading -->
    <div
      v-if="store.loading"
      class="mt-8 flex items-center justify-center p-8"
    >
      <span class="text-go4-muted dark:text-gray-400">Laden...</span>
    </div>

    <!-- Error -->
    <div
      v-else-if="store.error && !showGenerateForm"
      class="mt-8 rounded-lg bg-red-50 dark:bg-red-900/20 p-4 text-red-700 dark:text-red-400"
    >
      {{ store.error }}
    </div>

    <!-- Empty -->
    <div
      v-else-if="store.pieces.length === 0"
      class="mt-8"
    >
      <EmptyState title="Keine Content-Pieces gefunden" />
    </div>

    <!-- Card Grid -->
    <div
      v-else
      class="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"
    >
      <ContentCard
        v-for="piece in store.pieces"
        :key="piece.id"
        :piece="piece"
        @edit="handleEdit"
        @approve="handleApprove"
        @publish="handlePublish"
        @delete="handleDelete"
      />
    </div>
  </div>
</template>
