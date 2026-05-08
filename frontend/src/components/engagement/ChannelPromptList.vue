<script setup>
/**
 * Right-side card on Pipeline-Übersicht: lists channels with their prompt slots.
 * Each row is collapsible. Click on a slot or "+ Prompt anlegen" opens the
 * PromptEditorDrawer.
 */
import { ref, computed, onMounted, watch } from 'vue'
import { listPipelinePrompts } from '@/api/engagement'
import PromptEditorDrawer from './PromptEditorDrawer.vue'

const props = defineProps({
  pipelineId: { type: Number, required: true },
  pipelineChannels: { type: Array, default: () => [] },
})

const channelMeta = {
  email: { icon: '✉', label: 'Email' },
  letter: { icon: '✉', label: 'Brief' },
  whatsapp: { icon: '💬', label: 'WhatsApp' },
  linkedin: { icon: '🔗', label: 'LinkedIn' },
  phone: { icon: '📞', label: 'Telefon' },
}

const prompts = ref([])
const loading = ref(false)
const error = ref(null)
const expanded = ref({})  // channel -> bool

const drawerOpen = ref(false)
const drawerPrompt = ref(null)
const drawerChannel = ref('email')
const drawerSlot = ref('initial')

const channelsToShow = computed(() => {
  // Always show all configured channels of the pipeline + any channel that
  // already has a prompt (in case channels were removed but prompts remain).
  const set = new Set(props.pipelineChannels || [])
  prompts.value.forEach((p) => set.add(p.channel))
  // Stable order matching channelMeta keys, then any unknown ones
  const ordered = Object.keys(channelMeta).filter((c) => set.has(c))
  const extras = [...set].filter((c) => !channelMeta[c])
  return [...ordered, ...extras]
})

const promptsByChannel = computed(() => {
  const map = {}
  for (const p of prompts.value) {
    if (!map[p.channel]) map[p.channel] = []
    map[p.channel].push(p)
  }
  return map
})

async function fetchPrompts() {
  loading.value = true
  error.value = null
  try {
    const { data } = await listPipelinePrompts(props.pipelineId)
    prompts.value = data
    // Auto-expand channels that have prompts
    for (const ch of Object.keys(promptsByChannel.value)) {
      expanded.value[ch] = true
    }
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    loading.value = false
  }
}

watch(() => props.pipelineId, () => fetchPrompts())
onMounted(() => fetchPrompts())

function toggle(channel) {
  expanded.value[channel] = !expanded.value[channel]
}

function openCreate(channel) {
  drawerChannel.value = channel
  drawerSlot.value =
    promptsByChannel.value[channel]?.length ? 'followup_1' : 'initial'
  drawerPrompt.value = null
  drawerOpen.value = true
}

function openEdit(prompt) {
  drawerPrompt.value = prompt
  drawerChannel.value = prompt.channel
  drawerSlot.value = prompt.slot
  drawerOpen.value = true
}

function onSaved() {
  fetchPrompts()
}

function onDeleted() {
  fetchPrompts()
}
</script>

<template>
  <div class="rounded-lg bg-white p-5 shadow dark:bg-gray-800">
    <div class="mb-3 flex items-center justify-between">
      <h3 class="text-base font-semibold text-gray-900 dark:text-gray-100">Kanäle &amp; Prompts</h3>
      <span v-if="loading" class="text-xs text-gray-400">Laden…</span>
    </div>

    <div v-if="error" class="mb-3 rounded-md bg-red-50 p-2 text-xs text-red-700 dark:bg-red-900/20 dark:text-red-300">
      {{ error }}
    </div>

    <ul class="divide-y divide-gray-100 dark:divide-gray-700">
      <li v-for="ch in channelsToShow" :key="ch" class="py-2">
        <button
          type="button"
          class="flex w-full items-center justify-between rounded px-1 py-1 text-left transition hover:bg-gray-50 dark:hover:bg-gray-700/40"
          @click="toggle(ch)"
        >
          <span class="flex items-center gap-2">
            <span class="text-base">{{ channelMeta[ch]?.icon || '⚙' }}</span>
            <span class="text-sm font-medium text-gray-800 dark:text-gray-200">
              {{ channelMeta[ch]?.label || ch }}
            </span>
            <span
              class="ml-1 rounded-full bg-gray-100 px-1.5 py-0.5 text-[10px] font-medium text-gray-500 dark:bg-gray-700 dark:text-gray-400"
            >
              {{ promptsByChannel[ch]?.length || 0 }}
            </span>
          </span>
          <svg
            class="h-4 w-4 text-gray-400 transition"
            :class="expanded[ch] ? 'rotate-90' : ''"
            fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"
          >
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
          </svg>
        </button>

        <div v-if="expanded[ch]" class="mt-1 space-y-1 pl-7">
          <button
            v-for="p in promptsByChannel[ch] || []"
            :key="p.id"
            type="button"
            class="group flex w-full items-center justify-between rounded px-2 py-1.5 text-left text-sm transition hover:bg-go4-primary/5"
            @click="openEdit(p)"
          >
            <span class="flex items-center gap-2 min-w-0">
              <span class="text-xs text-gray-400 font-mono">{{ p.slot }}</span>
              <span class="truncate text-gray-700 dark:text-gray-200">{{ p.name }}</span>
              <span
                v-if="!p.is_active"
                class="rounded-full bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-500 dark:bg-gray-700 dark:text-gray-400"
              >
                inaktiv
              </span>
            </span>
            <svg
              class="h-3.5 w-3.5 text-gray-300 group-hover:text-go4-primary"
              fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
            </svg>
          </button>
          <button
            type="button"
            class="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-xs font-medium text-go4-primary transition hover:bg-go4-primary/5"
            @click="openCreate(ch)"
          >
            <span class="text-base leading-none">+</span>
            <span>Prompt anlegen</span>
          </button>
        </div>
      </li>
    </ul>

    <p v-if="!loading && channelsToShow.length === 0" class="text-sm text-gray-500 dark:text-gray-400">
      Keine Kanäle in dieser Pipeline aktiv.
    </p>

    <PromptEditorDrawer
      :open="drawerOpen"
      :pipeline-id="pipelineId"
      :prompt="drawerPrompt"
      :default-channel="drawerChannel"
      :default-slot="drawerSlot"
      @close="drawerOpen = false"
      @saved="onSaved"
      @deleted="onDeleted"
    />
  </div>
</template>
