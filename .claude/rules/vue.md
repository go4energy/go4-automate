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

## Tab-Routing und Breadcrumb-Navigation (STANDARD)

Tabs in Views MÜSSEN als echte Routen implementiert werden, nicht als UI-State. Das ermöglicht:
- Deep-Linking zu Tabs
- Browser-Vor/Zurück funktioniert
- Breadcrumb-Navigation zeigt den vollständigen Pfad

### Backend: Tab-Routen im Manifest
Jeder Tab braucht eine eigene Route in `__manifest__.py`:

```python
"frontend": {
    "base_route": "/linkedin",
    "routes": [
        # Hauptroute (Redirect oder Default-Tab)
        {
            "path": "",
            "name": "linkedin",
            "view": "LinkedInView",
            "meta": {
                "title": "LinkedIn",
                "breadcrumb": {"label": "LinkedIn"},
                "tab": "dashboard",  # Welcher Tab aktiv ist
            },
        },
        # Tab-Routen - alle nutzen dieselbe View
        {
            "path": "contacts",
            "name": "linkedin-contacts",
            "view": "LinkedInView",
            "meta": {
                "title": "Kontakte",
                "breadcrumb": {"label": "Kontakte", "parent": "linkedin"},
                "tab": "contacts",
            },
        },
        # Detail-Route mit parent-Referenz zum Tab
        {
            "path": "contacts/:id",
            "name": "linkedin-contact-detail",
            "view": "LinkedInContactDetailView",
            "props": True,
            "meta": {
                "title": "Kontakt-Details",
                "breadcrumb": {"label": "Details", "parent": "linkedin-contacts"},
            },
        },
    ],
}
```

### Frontend: Tab aus Route lesen
```javascript
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import Breadcrumb from '@/components/ui/Breadcrumb.vue'

const route = useRoute()

// Tab aus route.meta.tab lesen, NICHT aus ref() oder useTabState()
const activeTab = computed(() => route.meta?.tab || 'dashboard')

// Tabs mit Routen definieren
const tabs = [
  { key: 'dashboard', label: 'Dashboard', route: '/linkedin/dashboard' },
  { key: 'contacts', label: 'Kontakte', route: '/linkedin/contacts' },
]
```

### Frontend: Tab-Navigation als router-link
```html
<!-- Breadcrumb einbinden -->
<Breadcrumb class="mb-4" />

<!-- Tabs als router-link, NICHT als button -->
<nav class="-mb-px flex gap-6">
  <router-link
    v-for="tab in tabs"
    :key="tab.key"
    :to="tab.route"
    class="border-b-2 pb-3 text-sm font-medium"
    :class="activeTab === tab.key ? 'border-go4-primary' : 'border-transparent'"
  >
    {{ tab.label }}
  </router-link>
</nav>
```

### Breadcrumb-Hierarchie
Die `breadcrumb.parent` Referenz baut die Hierarchie auf:
```
Home / LinkedIn / Kontakte / Details
       ^          ^          ^
       |          |          +-- parent: "linkedin-contacts"
       |          +-- parent: "linkedin"
       +-- Kein parent (Modul-Ebene)
```

### Checkliste für neue Module mit Tabs
- [ ] Tab-Routen im Backend-Manifest definieren
- [ ] `meta.tab` für jeden Tab setzen
- [ ] `meta.breadcrumb` mit `label` und `parent` setzen
- [ ] Frontend: `useRoute()` statt `useTabState()`
- [ ] Frontend: `activeTab` als `computed()` aus `route.meta.tab`
- [ ] Frontend: Tabs als `router-link` statt `button`
- [ ] Frontend: `Breadcrumb` Komponente einbinden

## UI-Konventionen

### Action-Buttons ("+", "Neu", etc.)
- Action-Buttons gehören **unter die Tab-Leiste**, nicht in den PageHeader
- Position: In der gleichen Zeile wie Suchfeld/Filter, rechts ausgerichtet (`justify-between`)
- Beispiel: `[SearchInput]  ........................  [+ Neue Pipeline]`
- NIEMALS Action-Buttons im PageHeader `#actions` Slot platzieren

### ConfirmDialog Props
Die `ConfirmDialog` Komponente nutzt folgende Props:
- `:open` (NICHT `:show`) – Sichtbarkeit steuern
- `confirm-text` (NICHT `confirm-label`) – Text des Bestätigen-Buttons
- `variant` (NICHT `confirm-variant`) – "danger", "warning", "info"
- `@confirm` – Bestätigung-Event
- `@cancel` – Abbrechen-Event

## Verboten
- `var` – nutze `const` / `let`
- Options API (`data()`, `methods`, `computed` als Objekt)
- jQuery oder DOM-Manipulation
- Eigenes CSS / `<style>` Blöcke (nur Tailwind)
- `console.log` in Production Code (nur zum Debuggen, vor Commit entfernen)
- Loading ohne Error State (immer beides implementieren)
