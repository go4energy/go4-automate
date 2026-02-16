# Vue 3 Code Rules

## Grundregeln
- **Composition API** mit `<script setup>` – IMMER
- **JavaScript** – kein TypeScript
- **Tailwind CSS** nur – kein eigenes CSS, keine `<style>` Blöcke
- Design System: https://github.com/go4energy/go4-design-system.git

## Component Pattern
```vue
<script setup>
import { ref, computed, onMounted } from 'vue'
import { useLeadStore } from '@/stores/leads'

// Props
const props = defineProps({
  leadId: { type: Number, required: true },
  showDetails: { type: Boolean, default: false }
})

// Emits
const emit = defineEmits(['update', 'delete'])

// State
const loading = ref(false)
const error = ref(null)

// Store
const store = useLeadStore()

// Computed
const fullName = computed(() => `${store.lead?.firstName} ${store.lead?.lastName}`)

// Methods
async function fetchLead() {
  loading.value = true
  error.value = null
  try {
    await store.fetchLead(props.leadId)
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

// Lifecycle
onMounted(() => {
  fetchLead()
})
</script>

<template>
  <div v-if="loading" class="flex items-center justify-center p-8">
    <span class="text-gray-500">Laden...</span>
  </div>
  <div v-else-if="error" class="rounded-lg bg-red-50 p-4 text-red-700">
    {{ error }}
  </div>
  <div v-else class="space-y-4">
    <!-- Content -->
  </div>
</template>
```

## Dateistruktur
```
src/
  components/
    ui/          → Buttons, Inputs, Modals, Cards (wiederverwendbar)
    charts/      → ApexCharts Wrapper
    layout/      → Header, Sidebar, Footer
  views/         → Seiten (1 View = 1 Route)
  composables/   → useXyz() Funktionen (shared Logic)
  stores/        → Pinia Stores
  api/           → API Client + Endpoint-Funktionen
  router/        → Vue Router Config
```

## Benennung
- **Components**: `PascalCase.vue` → `LeadCard.vue`, `DataTable.vue`
- **Composables**: `useXyz.js` → `useLeads.js`, `useAuth.js`
- **Stores**: `xyz.js` → `leads.js`, `auth.js`
- **Views**: `XyzView.vue` → `LeadsView.vue`, `DashboardView.vue`

## Pinia Store Pattern (Setup Syntax)
```javascript
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import api from '@/api'

export const useLeadStore = defineStore('leads', () => {
  const leads = ref([])
  const loading = ref(false)

  const activeLeads = computed(() => leads.value.filter(l => l.status === 'active'))

  async function fetchLeads() {
    loading.value = true
    try {
      const { data } = await api.get('/leads')
      leads.value = data
    } finally {
      loading.value = false
    }
  }

  return { leads, loading, activeLeads, fetchLeads }
})
```

## API Client Pattern
- Axios Instanz in `src/api/index.js`
- Automatischer `X-Tenant-ID` Header via Interceptor
- Base URL aus `import.meta.env.VITE_API_URL`
- Response Error Interceptor mit zentralem Error-Handling

## Verboten
- `var` – nutze `const` / `let`
- Options API (`data()`, `methods`, `computed` als Objekt)
- jQuery oder DOM-Manipulation
- Eigenes CSS / `<style>` Blöcke (nur Tailwind)
- `console.log` in Production Code (nur zum Debuggen, vor Commit entfernen)
- Loading ohne Error State (immer beides implementieren)
