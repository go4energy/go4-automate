<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { usePromptStore } from '@/stores/prompts'
import PageHeader from '@/components/ui/PageHeader.vue'
import EmptyState from '@/components/ui/EmptyState.vue'

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
  content: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  analysis: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  email: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  general: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
  chat: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400',
  research: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400'
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
  router.push(`/settings/prompts/${promptId}`)
}

function goToNew() {
  router.push('/settings/prompts/new')
}

onMounted(() => {
  loadPrompts()
})
</script>

<template>
  <div>
    <PageHeader
      title="Prompt Registry"
      subtitle="KI-Prompts verwalten und testen"
    >
      <template #actions>
        <button
          class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90"
          @click="goToNew"
        >
          + Neuer Prompt
        </button>
      </template>
    </PageHeader>

    <!-- Filters -->
    <div class="mt-6 flex flex-wrap items-center gap-4">
      <input
        v-model="search"
        type="text"
        placeholder="Suchen..."
        class="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
        @input="loadPrompts"
      >
      <select
        v-model="categoryFilter"
        class="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
        @change="loadPrompts"
      >
        <option value="">
          Alle Kategorien
        </option>
        <option
          v-for="cat in categoryOptions"
          :key="cat"
          :value="cat"
        >
          {{ cat }}
        </option>
      </select>
      <select
        v-model="activeFilter"
        class="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
        @change="loadPrompts"
      >
        <option :value="null">
          Alle Status
        </option>
        <option :value="true">
          Aktiv
        </option>
        <option :value="false">
          Inaktiv
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
      v-else-if="store.error"
      class="mt-8 rounded-lg bg-red-50 dark:bg-red-900/20 p-4 text-red-700 dark:text-red-400"
    >
      {{ store.error }}
    </div>

    <!-- Empty State -->
    <div
      v-else-if="filteredPrompts.length === 0"
      class="mt-8"
    >
      <EmptyState title="Keine Prompts gefunden">
        <template #action>
          <button
            class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90"
            @click="goToNew"
          >
            Ersten Prompt erstellen
          </button>
        </template>
      </EmptyState>
    </div>

    <!-- Grid -->
    <div
      v-else
      class="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"
    >
      <div
        v-for="prompt in filteredPrompts"
        :key="prompt.id"
        class="cursor-pointer rounded-lg bg-white dark:bg-gray-800 p-5 shadow-sm transition hover:shadow-md"
        @click="goToEditor(prompt.id)"
      >
        <div class="flex items-start justify-between">
          <div class="min-w-0 flex-1">
            <h3 class="truncate text-sm font-semibold text-go4-secondary dark:text-gray-100">
              {{ prompt.name }}
            </h3>
            <p class="mt-0.5 font-mono text-xs text-go4-muted dark:text-gray-400">
              {{ prompt.slug }}
            </p>
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

        <p
          v-if="prompt.description"
          class="mt-2 line-clamp-2 text-xs text-go4-muted dark:text-gray-400"
        >
          {{ prompt.description }}
        </p>

        <div
          class="mt-3 flex items-center justify-between text-xs text-go4-muted dark:text-gray-400"
        >
          <span>{{ prompt.provider }} / {{ prompt.model }}</span>
          <div class="flex items-center gap-2">
            <span>v{{ prompt.version }}</span>
            <span
              :class="[
                'inline-block h-2 w-2 rounded-full',
                prompt.is_active ? 'bg-green-400' : 'bg-gray-300 dark:bg-gray-600'
              ]"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
