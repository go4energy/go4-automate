<script setup>
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, default: 'Dokumentation' },
  content: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  error: { type: String, default: null }
})

const emit = defineEmits(['close'])

const renderedContent = computed(() => marked.parse(props.content || ''))
</script>

<template>
  <div
    v-if="open"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
    @click.self="emit('close')"
  >
    <div class="flex h-[85vh] w-full max-w-5xl flex-col overflow-hidden rounded-xl bg-white shadow-2xl dark:bg-gray-800">
      <div class="flex items-center justify-between border-b border-gray-200 px-5 py-4 dark:border-gray-700">
        <div>
          <h2 class="text-lg font-semibold text-go4-secondary dark:text-gray-100">
            {{ title }}
          </h2>
          <p class="text-sm text-go4-muted dark:text-gray-400">
            Modul-Dokumentation
          </p>
        </div>
        <button
          class="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 transition hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
          @click="emit('close')"
        >
          Schliessen
        </button>
      </div>

      <div class="flex-1 overflow-y-auto px-6 py-5">
        <p
          v-if="loading"
          class="text-sm text-go4-muted dark:text-gray-400"
        >
          Dokumentation wird geladen...
        </p>
        <p
          v-else-if="error"
          class="rounded-lg bg-red-50 p-4 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400"
        >
          {{ error }}
        </p>
        <article
          v-else
          class="prose prose-sm prose-slate max-w-none prose-headings:text-go4-secondary prose-p:text-gray-700 prose-li:text-gray-700 prose-strong:text-go4-secondary prose-a:text-go4-primary prose-code:text-go4-secondary prose-pre:bg-gray-900 prose-pre:text-gray-100 dark:prose-invert dark:prose-headings:text-gray-100 dark:prose-p:text-gray-200 dark:prose-li:text-gray-200 dark:prose-strong:text-white dark:prose-code:text-gray-100 dark:prose-a:text-orange-300"
          v-html="renderedContent"
        />
      </div>
    </div>
  </div>
</template>
