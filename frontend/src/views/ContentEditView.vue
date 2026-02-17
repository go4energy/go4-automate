<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useContentStore } from '@/stores/content'

const route = useRoute()
const router = useRouter()
const store = useContentStore()

const saving = ref(false)
const approveModal = ref(false)
const scheduledDate = ref('')
const scheduledTime = ref('09:00')

const form = ref({
  title: '',
  caption: '',
  short: '',
  hashtags: '',
  hook: '',
  cta: '',
  platform: '',
  content_type: '',
  funnel_stage: '',
  buyer_persona: ''
})

const captionLength = computed(() => (form.value.caption || '').length)

const piece = computed(() => store.currentPiece)

async function loadPiece() {
  try {
    const data = await store.fetchPiece(route.params.id)
    form.value = {
      title: data.title || '',
      caption: data.caption || '',
      short: data.short || '',
      hashtags: data.hashtags || '',
      hook: data.hook || '',
      cta: data.cta || '',
      platform: data.platform || '',
      content_type: data.content_type || '',
      funnel_stage: data.funnel_stage || '',
      buyer_persona: data.buyer_persona || ''
    }
  } catch {
    // error is set in store
  }
}

async function handleSave() {
  saving.value = true
  try {
    await store.update(route.params.id, form.value)
  } catch {
    // error is set in store
  } finally {
    saving.value = false
  }
}

function openApproveModal() {
  const tomorrow = new Date()
  tomorrow.setDate(tomorrow.getDate() + 1)
  scheduledDate.value = tomorrow.toISOString().split('T')[0]
  scheduledTime.value = '09:00'
  approveModal.value = true
}

async function handleApprove() {
  const dt = new Date(`${scheduledDate.value}T${scheduledTime.value}:00`)
  try {
    await store.approve(route.params.id, {
      approved_by: 'editor',
      scheduled_at: dt.toISOString()
    })
    approveModal.value = false
  } catch {
    // error is set in store
  }
}

function goBack() {
  router.push('/content')
}

onMounted(() => {
  loadPiece()
})
</script>

<template>
  <div class="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
    <div class="flex items-center justify-between">
      <div>
        <button
          class="text-sm text-go4-muted hover:text-go4-secondary"
          @click="goBack"
        >
          &larr; Zurück zur Übersicht
        </button>
        <h1 class="mt-2 text-2xl font-bold text-go4-secondary">
          Content bearbeiten
        </h1>
      </div>
      <div
        v-if="piece"
        class="flex items-center gap-2"
      >
        <span
          class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
          :class="{
            'bg-yellow-100 text-yellow-800': piece.status === 'draft',
            'bg-blue-100 text-blue-800': piece.status === 'scheduled',
            'bg-green-100 text-green-800': piece.status === 'published',
            'bg-red-100 text-red-800': piece.status === 'failed'
          }"
        >
          {{ piece.status }}
        </span>
        <span
          v-if="piece.ai_model"
          class="text-xs text-go4-muted"
        > AI: {{ piece.ai_model }} </span>
      </div>
    </div>

    <!-- Loading -->
    <div
      v-if="store.loading && !piece"
      class="mt-8 flex items-center justify-center p-8"
    >
      <span class="text-go4-muted">Laden...</span>
    </div>

    <!-- Error -->
    <div
      v-else-if="store.error && !piece"
      class="mt-8 rounded-lg bg-red-50 p-4 text-red-700"
    >
      {{ store.error }}
    </div>

    <!-- Content -->
    <div
      v-else-if="piece"
      class="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2"
    >
      <!-- Left: Form -->
      <div class="space-y-4">
        <div>
          <label class="block text-xs font-medium text-go4-muted">Titel</label>
          <input
            v-model="form.title"
            type="text"
            class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
          >
        </div>

        <div>
          <label class="block text-xs font-medium text-go4-muted">
            Caption
            <span class="ml-1 text-go4-muted">({{ captionLength }}/2200)</span>
          </label>
          <textarea
            v-model="form.caption"
            rows="8"
            maxlength="2200"
            class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
          />
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-medium text-go4-muted">Hook</label>
            <input
              v-model="form.hook"
              type="text"
              class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
            >
          </div>
          <div>
            <label class="block text-xs font-medium text-go4-muted">CTA</label>
            <input
              v-model="form.cta"
              type="text"
              class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
            >
          </div>
        </div>

        <div>
          <label class="block text-xs font-medium text-go4-muted">Hashtags</label>
          <input
            v-model="form.hashtags"
            type="text"
            class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
          >
        </div>

        <div>
          <label class="block text-xs font-medium text-go4-muted">Kurzversion (max 280)</label>
          <textarea
            v-model="form.short"
            rows="2"
            maxlength="280"
            class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
          />
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-medium text-go4-muted">Plattform</label>
            <select
              v-model="form.platform"
              class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
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
            <label class="block text-xs font-medium text-go4-muted">Content-Typ</label>
            <select
              v-model="form.content_type"
              class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
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

        <!-- Actions -->
        <div class="flex items-center gap-3 pt-2">
          <button
            :disabled="saving"
            class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark disabled:opacity-50"
            @click="handleSave"
          >
            {{ saving ? 'Speichert...' : 'Speichern' }}
          </button>
          <button
            v-if="piece.status === 'draft'"
            class="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            @click="openApproveModal"
          >
            Genehmigen + Planen
          </button>
          <button
            class="rounded-lg bg-go4-surface px-4 py-2 text-sm font-medium text-go4-secondary hover:bg-gray-200"
            @click="goBack"
          >
            Zurück
          </button>
        </div>

        <p
          v-if="store.error"
          class="text-sm text-red-600"
        >
          {{ store.error }}
        </p>
      </div>

      <!-- Right: Live Preview -->
      <div class="rounded-lg bg-white p-6 shadow-sm">
        <h2 class="text-sm font-semibold text-go4-secondary">
          Vorschau
        </h2>
        <div class="mt-4 rounded-lg border border-gray-200 p-4">
          <div class="flex items-center gap-2">
            <div class="h-8 w-8 rounded-full bg-go4-primary" />
            <div>
              <p class="text-xs font-semibold text-go4-secondary">
                Unternehmen
              </p>
              <p class="text-xs text-go4-muted">
                {{ form.platform }} &middot; Jetzt
              </p>
            </div>
          </div>
          <p
            v-if="form.hook"
            class="mt-3 text-sm font-semibold text-go4-secondary"
          >
            {{ form.hook }}
          </p>
          <p class="mt-2 whitespace-pre-line text-sm text-go4-secondary">
            {{ form.caption }}
          </p>
          <p
            v-if="form.hashtags"
            class="mt-2 text-sm text-blue-600"
          >
            {{ form.hashtags }}
          </p>
          <p
            v-if="form.cta"
            class="mt-3 text-sm font-medium text-go4-primary"
          >
            {{ form.cta }}
          </p>
        </div>

        <!-- Scheduling Info -->
        <div
          v-if="piece.scheduled_at"
          class="mt-4 rounded-lg bg-blue-50 p-3"
        >
          <p class="text-xs font-medium text-blue-800">
            Geplant: {{ new Date(piece.scheduled_at).toLocaleString('de-DE') }}
          </p>
          <p
            v-if="piece.approved_by"
            class="mt-1 text-xs text-blue-600"
          >
            Genehmigt von: {{ piece.approved_by }}
          </p>
        </div>

        <!-- Error Info -->
        <div
          v-if="piece.error_message"
          class="mt-4 rounded-lg bg-red-50 p-3"
        >
          <p class="text-xs font-medium text-red-800">
            Fehler: {{ piece.error_message }}
          </p>
        </div>
      </div>
    </div>

    <!-- Approve Modal -->
    <div
      v-if="approveModal"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
    >
      <div class="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <h2 class="text-lg font-semibold text-go4-secondary">
          Post genehmigen
        </h2>
        <p class="mt-1 text-sm text-go4-muted">
          Wähle Datum und Uhrzeit für die Veröffentlichung.
        </p>
        <div class="mt-4 grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-medium text-go4-muted">Datum</label>
            <input
              v-model="scheduledDate"
              type="date"
              class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
            >
          </div>
          <div>
            <label class="block text-xs font-medium text-go4-muted">Uhrzeit</label>
            <input
              v-model="scheduledTime"
              type="time"
              class="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
            >
          </div>
        </div>
        <div class="mt-6 flex items-center justify-end gap-3">
          <button
            class="rounded-lg bg-go4-surface px-4 py-2 text-sm font-medium text-go4-secondary hover:bg-gray-200"
            @click="approveModal = false"
          >
            Abbrechen
          </button>
          <button
            class="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            @click="handleApprove"
          >
            Genehmigen
          </button>
        </div>
        <p
          v-if="store.error"
          class="mt-2 text-sm text-red-600"
        >
          {{ store.error }}
        </p>
      </div>
    </div>
  </div>
</template>
