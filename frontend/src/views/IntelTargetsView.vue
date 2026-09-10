<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useIntelStore } from '@/stores/intel'
import PageHeader from '@/components/ui/PageHeader.vue'

const route = useRoute()
const store = useIntelStore()

const tabs = [
  { key: 'dashboard', label: 'Dashboard', route: '/intel' },
  { key: 'targets', label: 'Targets', route: '/intel/targets' },
  { key: 'briefings', label: 'Briefings', route: '/intel/briefings' },
  { key: 'events', label: 'Events', route: '/intel/events' }
]
const activeTab = computed(() => route.meta?.tab || 'targets')

const showCreate = ref(false)
const form = ref({ name: '', kind: 'competitor', is_active: true })

onMounted(() => store.fetchTargets())

async function submit() {
  if (!form.value.name.trim()) return
  await store.createTarget({
    name: form.value.name.trim(),
    kind: form.value.kind,
    is_active: form.value.is_active,
    context: {}
  })
  form.value = { name: '', kind: 'competitor', is_active: true }
  showCreate.value = false
}

async function toggle(t) {
  await store.updateTarget(t.id, { is_active: !t.is_active })
}

async function remove(t) {
  if (!confirm(`Watch-Target "${t.name}" deaktivieren?`)) return
  await store.deleteTarget(t.id)
}

const kindBadge = {
  competitor: ['Wettbewerber', 'bg-orange-100 text-orange-800'],
  regulator: ['Regulator', 'bg-blue-100 text-blue-800'],
  segment: ['Markt-Segment', 'bg-purple-100 text-purple-800']
}
</script>

<template>
  <div>
    <PageHeader title="Intel" info-module="intel" />

    <nav class="mb-6 border-b border-gray-200 dark:border-gray-700">
      <div class="-mb-px flex gap-6">
        <router-link
          v-for="t in tabs"
          :key="t.key"
          :to="t.route"
          class="border-b-2 pb-3 text-sm font-medium transition"
          :class="
            activeTab === t.key
              ? 'border-go4-primary text-go4-primary'
              : 'border-transparent text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200'
          "
        >
          {{ t.label }}
        </router-link>
      </div>
    </nav>

    <div class="mb-4 flex items-center justify-between gap-3">
      <p class="text-sm text-go4-muted dark:text-gray-400">
        {{ store.targets.length }} Watch-Targets
      </p>
      <button
        type="button"
        class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark"
        @click="showCreate = !showCreate"
      >
        {{ showCreate ? '× Abbrechen' : '+ Neues Target' }}
      </button>
    </div>

    <div
      v-if="showCreate"
      class="mb-6 rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
    >
      <div class="grid gap-3 sm:grid-cols-[1fr_220px_auto]">
        <input
          v-model="form.name"
          type="text"
          placeholder="Name (z.B. Stromnetz GmbH)"
          class="rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
        >
        <select
          v-model="form.kind"
          class="rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
        >
          <option value="competitor">Wettbewerber</option>
          <option value="regulator">Regulator</option>
          <option value="segment">Markt-Segment</option>
        </select>
        <button
          type="button"
          class="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700"
          @click="submit"
        >
          Anlegen
        </button>
      </div>
    </div>

    <div v-if="store.loading" class="text-sm text-go4-muted dark:text-gray-400">
      Laden…
    </div>
    <div
      v-else-if="store.targets.length === 0"
      class="rounded-lg border-2 border-dashed border-gray-200 p-12 text-center text-sm text-go4-muted dark:border-gray-700 dark:text-gray-400"
    >
      Keine Watch-Targets vorhanden — lege oben das erste an.
    </div>
    <ul v-else class="space-y-2">
      <li
        v-for="t in store.targets"
        :key="t.id"
        class="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
      >
        <div class="flex items-center gap-3">
          <span
            class="inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium"
            :class="kindBadge[t.kind]?.[1] || 'bg-gray-100 text-gray-700'"
          >
            {{ kindBadge[t.kind]?.[0] || t.kind }}
          </span>
          <router-link
            :to="`/intel/targets/${t.id}`"
            class="font-medium text-go4-secondary hover:text-go4-primary dark:text-gray-100"
          >
            {{ t.name }}
          </router-link>
          <span
            v-if="!t.is_active"
            class="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-500"
          >
            inaktiv
          </span>
        </div>
        <div class="flex items-center gap-3">
          <button
            type="button"
            class="text-xs text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200"
            @click="toggle(t)"
          >
            {{ t.is_active ? 'Pause' : 'Aktivieren' }}
          </button>
          <button
            type="button"
            class="text-xs text-red-500 hover:text-red-700"
            @click="remove(t)"
          >
            Entfernen
          </button>
        </div>
      </li>
    </ul>
  </div>
</template>
