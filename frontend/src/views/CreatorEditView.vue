<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCreatorStore } from '@/stores/creator'
import PageHeader from '@/components/ui/PageHeader.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import TagSelector from '@/components/ui/TagSelector.vue'
import StreamSelector from '@/components/ui/StreamSelector.vue'

const route = useRoute()
const router = useRouter()
const store = useCreatorStore()

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
  buyer_persona: '',
  tags: [],
  streams: []
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
      buyer_persona: data.buyer_persona || '',
      tags: data.tags || [],
      streams: data.streams || []
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
  router.push('/creator')
}

onMounted(() => {
  loadPiece()
})
</script>

<template>
  <div>
    <PageHeader title="Content bearbeiten">
      <template #actions>
        <div v-if="piece" class="flex items-center gap-2">
          <StatusBadge :status="piece.status" />
          <span v-if="piece.ai_model" class="text-xs text-go4-muted dark:text-gray-400">
            AI: {{ piece.ai_model }}
          </span>
        </div>
      </template>
    </PageHeader>

    <!-- Loading -->
    <div v-if="store.loading && !piece" class="mt-8 flex items-center justify-center p-8">
      <span class="text-go4-muted dark:text-gray-400">Laden...</span>
    </div>

    <!-- Error -->
    <div
      v-else-if="store.error && !piece"
      class="mt-8 rounded-lg bg-red-50 dark:bg-red-900/20 p-4 text-red-700 dark:text-red-400"
    >
      {{ store.error }}
    </div>

    <!-- Content -->
    <div v-else-if="piece" class="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
      <!-- Left: Form -->
      <div class="space-y-4">
        <div>
          <label class="block text-xs font-medium text-go4-muted dark:text-gray-400">Titel</label>
          <input
            v-model="form.title"
            type="text"
            class="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
          />
        </div>

        <div>
          <label class="block text-xs font-medium text-go4-muted dark:text-gray-400">
            Caption
            <span class="ml-1 text-go4-muted dark:text-gray-400">({{ captionLength }}/2200)</span>
          </label>
          <textarea
            v-model="form.caption"
            rows="8"
            maxlength="2200"
            class="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
          />
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-medium text-go4-muted dark:text-gray-400">Hook</label>
            <input
              v-model="form.hook"
              type="text"
              class="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
            />
          </div>
          <div>
            <label class="block text-xs font-medium text-go4-muted dark:text-gray-400">CTA</label>
            <input
              v-model="form.cta"
              type="text"
              class="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
            />
          </div>
        </div>

        <div>
          <label class="block text-xs font-medium text-go4-muted dark:text-gray-400"
            >Hashtags</label
          >
          <input
            v-model="form.hashtags"
            type="text"
            class="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
          />
        </div>

        <div>
          <label class="block text-xs font-medium text-go4-muted dark:text-gray-400"
            >Kurzversion (max 280)</label
          >
          <textarea
            v-model="form.short"
            rows="2"
            maxlength="280"
            class="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
          />
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-medium text-go4-muted dark:text-gray-400"
              >Plattform</label
            >
            <select
              v-model="form.platform"
              class="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
            >
              <option value="facebook">Facebook</option>
              <option value="instagram">Instagram</option>
              <option value="linkedin">LinkedIn</option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-medium text-go4-muted dark:text-gray-400"
              >Content-Typ</label
            >
            <select
              v-model="form.content_type"
              class="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
            >
              <option value="post">Post</option>
              <option value="story">Story</option>
              <option value="reel">Reel</option>
              <option value="carousel">Carousel</option>
            </select>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-medium text-go4-muted dark:text-gray-400">Tags</label>
            <div class="mt-1">
              <TagSelector v-model="form.tags" placeholder="Tags auswaehlen..." />
            </div>
          </div>
          <div>
            <label class="block text-xs font-medium text-go4-muted dark:text-gray-400"
              >Streams</label
            >
            <div class="mt-1">
              <StreamSelector v-model="form.streams" placeholder="Streams auswaehlen..." />
            </div>
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
            class="rounded-lg bg-go4-surface px-4 py-2 text-sm font-medium text-go4-secondary dark:text-gray-100 hover:bg-gray-200 dark:hover:bg-gray-600"
            @click="goBack"
          >
            Zurueck
          </button>
        </div>

        <p v-if="store.error" class="text-sm text-red-600 dark:text-red-400">
          {{ store.error }}
        </p>
      </div>

      <!-- Right: Live Preview -->
      <div class="rounded-lg bg-white dark:bg-gray-800 p-6 shadow-sm">
        <h2 class="text-sm font-semibold text-go4-secondary dark:text-gray-100">Vorschau</h2>
        <div class="mt-4 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <div class="flex items-center gap-2">
            <div class="h-8 w-8 rounded-full bg-go4-primary" />
            <div>
              <p class="text-xs font-semibold text-go4-secondary dark:text-gray-100">Unternehmen</p>
              <p class="text-xs text-go4-muted dark:text-gray-400">
                {{ form.platform }} &middot; Jetzt
              </p>
            </div>
          </div>
          <p
            v-if="form.hook"
            class="mt-3 text-sm font-semibold text-go4-secondary dark:text-gray-100"
          >
            {{ form.hook }}
          </p>
          <p class="mt-2 whitespace-pre-line text-sm text-go4-secondary dark:text-gray-100">
            {{ form.caption }}
          </p>
          <p v-if="form.hashtags" class="mt-2 text-sm text-blue-600 dark:text-blue-400">
            {{ form.hashtags }}
          </p>
          <p v-if="form.cta" class="mt-3 text-sm font-medium text-go4-primary">
            {{ form.cta }}
          </p>
        </div>

        <!-- Scheduling Info -->
        <div v-if="piece.scheduled_at" class="mt-4 rounded-lg bg-blue-50 dark:bg-blue-900/20 p-3">
          <p class="text-xs font-medium text-blue-800 dark:text-blue-400">
            Geplant: {{ new Date(piece.scheduled_at).toLocaleString('de-DE') }}
          </p>
          <p v-if="piece.approved_by" class="mt-1 text-xs text-blue-600 dark:text-blue-400">
            Genehmigt von: {{ piece.approved_by }}
          </p>
        </div>

        <!-- Error Info -->
        <div v-if="piece.error_message" class="mt-4 rounded-lg bg-red-50 dark:bg-red-900/20 p-3">
          <p class="text-xs font-medium text-red-800 dark:text-red-400">
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
      <div class="w-full max-w-md rounded-lg bg-white dark:bg-gray-800 p-6 shadow-xl">
        <h2 class="text-lg font-semibold text-go4-secondary dark:text-gray-100">Post genehmigen</h2>
        <p class="mt-1 text-sm text-go4-muted dark:text-gray-400">
          Waehle Datum und Uhrzeit fuer die Veroeffentlichung.
        </p>
        <div class="mt-4 grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-medium text-go4-muted dark:text-gray-400">Datum</label>
            <input
              v-model="scheduledDate"
              type="date"
              class="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
            />
          </div>
          <div>
            <label class="block text-xs font-medium text-go4-muted dark:text-gray-400"
              >Uhrzeit</label
            >
            <input
              v-model="scheduledTime"
              type="time"
              class="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
            />
          </div>
        </div>
        <div class="mt-6 flex items-center justify-end gap-3">
          <button
            class="rounded-lg bg-go4-surface px-4 py-2 text-sm font-medium text-go4-secondary dark:text-gray-100 hover:bg-gray-200 dark:hover:bg-gray-600"
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
        <p v-if="store.error" class="mt-2 text-sm text-red-600 dark:text-red-400">
          {{ store.error }}
        </p>
      </div>
    </div>
  </div>
</template>
