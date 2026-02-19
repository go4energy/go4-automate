<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { usePromptStore } from '@/stores/prompts'

const router = useRouter()
const store = usePromptStore()

const search = ref('')
const categoryFilter = ref('')
const activeFilter = ref(null)

const filteredPrompts = computed(() => {
  return store.prompts
})

const categoryOptions = computed(() => {
  const cats = new Set(store.prompts.map((p) => p.category))
  return [...cats].sort()
})

const categoryColors = {
  content: 'bg-blue-100 text-blue-700',
  analysis: 'bg-purple-100 text-purple-700',
  email: 'bg-green-100 text-green-700',
  general: 'bg-gray-100 text-gray-700'
}

function getCategoryColor(category) {
  return categoryColors[category] || categoryColors.general
}

async function loadPrompts() {
  const params = {}
  if (search.value) params.search = search.value
  if (categoryFilter.value) params.category = categoryFilter.value
  if (activeFilter.value !== null) params.is_active = activeFilter.value
  await store.fetchPrompts(params)
}

function goToEditor(promptId) {
  router.push(`/prompts/${promptId}`)
}

function goToNew() {
  router.push('/prompts/new')
}

onMounted(() => {
  loadPrompts()
})
</script>

<template>
  <div class="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-go4-secondary">Prompt Registry</h1>
        <p class="mt-1 text-go4-muted">KI-Prompts verwalten und testen</p>
      </div>
      <button
        class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90"
        @click="goToNew"
      >
        + Neuer Prompt
      </button>
    </div>

    <!-- Filters -->
    <div class="mt-6 flex flex-wrap items-center gap-4">
      <input
        v-model="search"
        type="text"
        placeholder="Suchen..."
        class="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
        @input="loadPrompts"
      />
      <select
        v-model="categoryFilter"
        class="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none"
        @change="loadPrompts"
      >
        <option value="">Alle Kategorien</option>
        <option v-for="cat in categoryOptions" :key="cat" :value="cat">
          {{ cat }}
        </option>
      </select>
      <select
        v-model="activeFilter"
        class="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none"
        @change="loadPrompts"
      >
        <option :value="null">Alle Status</option>
        <option :value="true">Aktiv</option>
        <option :value="false">Inaktiv</option>
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
    <div
      v-else-if="filteredPrompts.length === 0"
      class="mt-8 rounded-lg border-2 border-dashed border-gray-300 p-12 text-center"
    >
      <p class="text-go4-muted">Keine Prompts gefunden.</p>
      <button
        class="mt-4 rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90"
        @click="goToNew"
      >
        Ersten Prompt erstellen
      </button>
    </div>

    <!-- Grid -->
    <div v-else class="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <div
        v-for="prompt in filteredPrompts"
        :key="prompt.id"
        class="cursor-pointer rounded-lg bg-white p-5 shadow-sm transition hover:shadow-md"
        @click="goToEditor(prompt.id)"
      >
        <div class="flex items-start justify-between">
          <div class="min-w-0 flex-1">
            <h3 class="truncate text-sm font-semibold text-go4-secondary">
              {{ prompt.name }}
            </h3>
            <p class="mt-0.5 font-mono text-xs text-go4-muted">{{ prompt.slug }}</p>
          </div>
          <span
            :class="[
              'ml-2 inline-flex shrink-0 rounded-full px-2 py-0.5 text-xs font-medium',
              getCategoryColor(prompt.category)
            ]"
          >
            {{ prompt.category }}
          </span>
        </div>

        <p v-if="prompt.description" class="mt-2 line-clamp-2 text-xs text-go4-muted">
          {{ prompt.description }}
        </p>

        <div class="mt-3 flex items-center justify-between text-xs text-go4-muted">
          <span>{{ prompt.provider }} / {{ prompt.model }}</span>
          <div class="flex items-center gap-2">
            <span>v{{ prompt.version }}</span>
            <span
              :class="[
                'inline-block h-2 w-2 rounded-full',
                prompt.is_active ? 'bg-green-400' : 'bg-gray-300'
              ]"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
