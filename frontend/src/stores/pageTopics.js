import { ref } from 'vue'
import { defineStore } from 'pinia'

/**
 * Page-Topics — declared by views/components when they mount.
 *
 * The chat panel reads this to show "Hilfe verfuegbar zu: X / Y"
 * suggestions, and the header chat icon turns green when topics > 0.
 *
 * Each topic entry: { topic, title, context, suggestions }
 *  - topic: ID matching backend chat_topics registry
 *  - title: optional override; falls back to backend topic title
 *  - context: { module, page, form_state } sent on first message
 *  - suggestions: array of starter-prompt strings
 */
export const usePageTopics = defineStore('pageTopics', () => {
  const topics = ref([])

  function setTopics(list) {
    topics.value = Array.isArray(list) ? list : []
  }

  function clearTopics() {
    topics.value = []
  }

  return { topics, setTopics, clearTopics }
})
