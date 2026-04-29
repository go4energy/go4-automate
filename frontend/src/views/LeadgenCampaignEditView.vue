<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLeadgenStore } from '@/stores/leadgen'
import { useEngagementStore } from '@/stores/engagement'
import PageHeader from '@/components/ui/PageHeader.vue'

const props = defineProps({
  id: { type: [String, Number], default: null }
})

const route = useRoute()
const router = useRouter()
const store = useLeadgenStore()
const engagement = useEngagementStore()

const isEdit = computed(() => Boolean(props.id || route.params.id))
const mode = ref('wizard')
const wizardStep = ref(1)
const saving = ref(false)
const localError = ref(null)

const form = ref({
  name: '',
  slug: '',
  description: '',
  queries_text: '',
  language: 'de',
  region: 'DE',
  target_match_threshold: 5,
  target_engagement_pipeline_id: null,
  create_new_pipeline: false,
  source: 'google_places',
  source_config: {
    search_modes: { nearby: true, text: true },
    nearby_types: [],
    text_synonyms: [],
    geographic: {
      mode: 'germany',
      bundesland: null,
      center_lat: null,
      center_lng: null,
      radius_km: 30
    },
    min_tile_km: 10,
    max_api_calls: 2000,
    pipeline_mode: 'smart',
    impressum: {
      max_concurrency: 5,
      max_places_per_run: 2000,
      http_timeout_s: 15
    },
    llm: {
      target_profile: '',
      output_description: '',
      prompt_template: '',
      model: 'claude-haiku-4-5',
      max_concurrency: 5,
      max_places_per_run: 2000,
      http_timeout_s: 15,
      max_html_chars: 15000
    }
  }
})

const intake = ref({
  loading: false,
  result: null,
  error: null
})

const canRunIntake = computed(
  () => !intake.value.loading && form.value.description.trim().length >= 3
)

const bundeslaender = [
  ['baden_wuerttemberg', 'Baden-Württemberg'],
  ['bayern', 'Bayern'],
  ['berlin', 'Berlin'],
  ['brandenburg', 'Brandenburg'],
  ['bremen', 'Bremen'],
  ['hamburg', 'Hamburg'],
  ['hessen', 'Hessen'],
  ['mecklenburg_vorpommern', 'Mecklenburg-Vorpommern'],
  ['niedersachsen', 'Niedersachsen'],
  ['nordrhein_westfalen', 'Nordrhein-Westfalen'],
  ['rheinland_pfalz', 'Rheinland-Pfalz'],
  ['saarland', 'Saarland'],
  ['sachsen', 'Sachsen'],
  ['sachsen_anhalt', 'Sachsen-Anhalt'],
  ['schleswig_holstein', 'Schleswig-Holstein'],
  ['thueringen', 'Thüringen']
]

const supportedTypes = [
  'electrician', 'plumber', 'roofing_contractor', 'general_contractor',
  'painter', 'locksmith', 'car_dealer', 'car_repair',
  'furniture_store', 'home_goods_store', 'hardware_store',
  'real_estate_agency', 'moving_company', 'storage',
  'lawyer', 'accounting', 'insurance_agency',
  'dentist', 'doctor', 'veterinary_care',
  'restaurant', 'cafe', 'bakery', 'hair_care', 'beauty_salon',
  'gym', 'travel_agency'
]

const costPreview = computed(() => {
  const maxCalls = Number(form.value.source_config.max_api_calls) || 0
  const usd = maxCalls * 0.032
  return {
    calls: maxCalls,
    usd: usd.toFixed(2)
  }
})

const canStartRun = computed(() => {
  const sc = form.value.source_config
  const hasQueries = form.value.queries_text.trim().length > 0
  const hasHybrid = (sc.nearby_types && sc.nearby_types.length > 0)
    || (sc.text_synonyms && sc.text_synonyms.length > 0)
  return hasQueries || hasHybrid
})

onMounted(async () => {
  await engagement.fetchPipelines({})
  if (isEdit.value) {
    mode.value = 'expert'
    const campaign = await store.fetchCampaign(props.id || route.params.id)
    if (campaign) {
      form.value.name = campaign.name
      form.value.slug = campaign.slug
      form.value.description = campaign.description || ''
      form.value.queries_text = (campaign.queries || []).join('\n')
      form.value.language = campaign.language
      form.value.region = campaign.region
      form.value.target_match_threshold = campaign.target_match_threshold
      form.value.target_engagement_pipeline_id = campaign.target_engagement_pipeline_id
      form.value.source = campaign.source || 'google_places'
      const sc = campaign.source_config || {}
      form.value.source_config = {
        search_modes: sc.search_modes || { nearby: true, text: true },
        nearby_types: sc.nearby_types || [],
        text_synonyms: sc.text_synonyms || [],
        geographic: sc.geographic || {
          mode: 'germany', bundesland: null,
          center_lat: null, center_lng: null, radius_km: 30
        },
        min_tile_km: sc.min_tile_km ?? 10,
        max_api_calls: sc.max_api_calls ?? 2000,
        pipeline_mode: sc.pipeline_mode ?? 'smart',
        impressum: {
          max_concurrency: sc.impressum?.max_concurrency ?? 5,
          max_places_per_run: sc.impressum?.max_places_per_run ?? 2000,
          http_timeout_s: sc.impressum?.http_timeout_s ?? 15
        },
        llm: {
          target_profile: sc.llm?.target_profile ?? '',
          output_description: sc.llm?.output_description ?? '',
          prompt_template: sc.llm?.prompt_template ?? '',
          model: sc.llm?.model ?? 'claude-haiku-4-5',
          max_concurrency: sc.llm?.max_concurrency ?? 5,
          max_places_per_run: sc.llm?.max_places_per_run ?? 2000,
          http_timeout_s: sc.llm?.http_timeout_s ?? 15,
          max_html_chars: sc.llm?.max_html_chars ?? 15000
        }
      }
    }
  }
})

function slugify(s) {
  return s
    .toLowerCase()
    .replace(/[äöüß]/g, (m) => ({ ä: 'ae', ö: 'oe', ü: 'ue', ß: 'ss' })[m])
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 100)
}

function autoSlug() {
  if (!form.value.slug && form.value.name) {
    form.value.slug = slugify(form.value.name)
  }
}

async function runIntake() {
  const text = form.value.description.trim()
  if (text.length < 3) return
  intake.value.loading = true
  intake.value.error = null
  try {
    const result = await store.suggestParameters(text)
    intake.value.result = result
    if (!result) return

    // Identity (only fill if user hasn't set anything yet)
    if (!form.value.name && result.name_suggestion) {
      form.value.name = result.name_suggestion
    }
    if (!isEdit.value && !form.value.slug && result.slug_suggestion) {
      form.value.slug = result.slug_suggestion
    } else if (!form.value.slug) {
      autoSlug()
    }

    // Search params
    if (result.search_modes) {
      form.value.source_config.search_modes = {
        nearby: result.search_modes.nearby !== false,
        text: result.search_modes.text !== false
      }
    }
    form.value.source_config.nearby_types = result.nearby_types || []
    form.value.source_config.text_synonyms = result.text_synonyms || []
    if (result.geographic) {
      form.value.source_config.geographic = {
        mode: result.geographic.mode || 'germany',
        bundesland: result.geographic.bundesland || null,
        center_lat: result.geographic.center_lat || null,
        center_lng: result.geographic.center_lng || null,
        radius_km: result.geographic.radius_km || 30
      }
    }
    if (result.min_tile_km) form.value.source_config.min_tile_km = result.min_tile_km
    if (result.max_api_calls) form.value.source_config.max_api_calls = result.max_api_calls
    if (result.pipeline_mode) form.value.source_config.pipeline_mode = result.pipeline_mode

    // Stage-3 LLM scaffolding
    if (result.target_profile) {
      form.value.source_config.llm.target_profile = result.target_profile
    }
    if (result.output_description) {
      form.value.source_config.llm.output_description = result.output_description
    }
    if (result.llm_prompt_template) {
      form.value.source_config.llm.prompt_template = result.llm_prompt_template
    }

    // Jump into the wizard at step 1 so the user can review every field.
    mode.value = 'wizard'
    wizardStep.value = 1
  } catch (e) {
    intake.value.error = e.response?.data?.detail || e.message || 'KI-Vorschlag fehlgeschlagen'
  } finally {
    intake.value.loading = false
  }
}

function addType(t) {
  if (!form.value.source_config.nearby_types.includes(t)) {
    form.value.source_config.nearby_types.push(t)
  }
}

function removeType(t) {
  form.value.source_config.nearby_types = form.value.source_config.nearby_types.filter((x) => x !== t)
}

function addSynonym() {
  const syn = (document.getElementById('syn-input') || {}).value
  if (syn && !form.value.source_config.text_synonyms.includes(syn)) {
    form.value.source_config.text_synonyms.push(syn)
    document.getElementById('syn-input').value = ''
  }
}

function removeSynonym(s) {
  form.value.source_config.text_synonyms = form.value.source_config.text_synonyms.filter((x) => x !== s)
}

function goNext() {
  if (wizardStep.value < 6) wizardStep.value++
}

function goPrev() {
  if (wizardStep.value > 1) wizardStep.value--
}

async function save() {
  localError.value = null
  saving.value = true
  try {
    const queries = form.value.queries_text
      .split('\n')
      .map((s) => s.trim())
      .filter((s) => s.length > 0)
    const payload = {
      name: form.value.name,
      slug: form.value.slug,
      description: form.value.description || null,
      queries,
      language: form.value.language,
      region: form.value.region,
      target_match_threshold: form.value.target_match_threshold,
      target_engagement_pipeline_id: form.value.target_engagement_pipeline_id || null,
      source: form.value.source,
      source_config: form.value.source_config
    }
    if (isEdit.value) {
      await store.saveCampaign(props.id || route.params.id, payload)
    } else {
      payload.create_new_pipeline = form.value.create_new_pipeline
      const created = await store.createNewCampaign(payload)
      if (created) {
        router.push(`/leadgen/campaigns/${created.id}`)
        return
      }
    }
    router.push('/leadgen/campaigns')
  } catch (e) {
    localError.value = e.response?.data?.detail || e.message || 'Speichern fehlgeschlagen'
  } finally {
    saving.value = false
  }
}

function cancel() {
  router.push('/leadgen/campaigns')
}
</script>

<template>
  <div class="space-y-4">
    <PageHeader :title="isEdit ? 'Kampagne bearbeiten' : 'Neue Kampagne'" />

    <!-- Mode toggle -->
    <div class="flex items-center gap-2 rounded-lg border border-gray-200 bg-white p-1 dark:border-gray-700 dark:bg-gray-800 w-fit">
      <button
        type="button"
        :class="[
          'rounded-md px-3 py-1.5 text-sm font-medium transition',
          mode === 'wizard' ? 'bg-go4-primary text-white' : 'text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700'
        ]"
        @click="mode = 'wizard'"
      >
        🧙 Wizard
      </button>
      <button
        type="button"
        :class="[
          'rounded-md px-3 py-1.5 text-sm font-medium transition',
          mode === 'expert' ? 'bg-go4-primary text-white' : 'text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700'
        ]"
        @click="mode = 'expert'"
      >
        ⚙️ Expertenmodus
      </button>
    </div>

    <!-- Shared header fields -->
    <section class="space-y-4 rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium mb-1">Name</label>
          <input
            v-model="form.name"
            type="text"
            required
            maxlength="200"
            class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700"
            @blur="autoSlug"
          >
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Slug</label>
          <input
            v-model="form.slug"
            type="text"
            required
            maxlength="100"
            pattern="^[a-z0-9-]+$"
            :disabled="isEdit"
            class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-mono disabled:opacity-60 dark:border-gray-600 dark:bg-gray-700"
          >
        </div>
      </div>
      <div>
        <label class="block text-sm font-medium mb-1">
          Beschreibung
          <span class="ml-1 text-xs font-normal text-gray-500">
            — wird auch als Briefing für die KI-Befüllung verwendet
          </span>
        </label>
        <textarea
          v-model="form.description"
          rows="4"
          placeholder="Beschreibe in 2-5 Sätzen, wen du finden willst und warum. Z.B. Branche, Region, was deine Lösung macht, welche Firmen passen."
          class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700"
        />
      </div>

      <!-- KI-Befüllung -->
      <div class="rounded-lg bg-blue-50 dark:bg-blue-900/30 p-4 space-y-3">
        <div class="flex items-start justify-between gap-4">
          <div class="text-sm text-gray-700 dark:text-gray-200">
            <div class="font-medium">
              🤖 Wizard mit KI befüllen
            </div>
            <div class="text-xs text-gray-600 dark:text-gray-400">
              Claude Haiku schlägt Name, Suchparameter, Geografie, Pipeline-Modus und Ziel-Profil aus deiner Beschreibung vor.
            </div>
          </div>
          <button
            type="button"
            :disabled="!canRunIntake"
            class="shrink-0 rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            @click="runIntake"
          >
            {{ intake.loading ? 'KI denkt…' : '🤖 Vorschlag erzeugen' }}
          </button>
        </div>
        <div
          v-if="intake.error"
          class="rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/40 dark:text-red-200"
        >
          {{ intake.error }}
        </div>
        <div
          v-if="intake.result"
          class="rounded-lg bg-white dark:bg-gray-800 p-3 text-xs space-y-1 border border-blue-200 dark:border-blue-800"
        >
          <div><strong>Begründung:</strong> {{ intake.result.reasoning }}</div>
          <div>
            <strong>Schätzung:</strong>
            {{ intake.result.estimated_calls_low }}–{{ intake.result.estimated_calls_high }} Calls
            ({{ intake.result.estimated_cost_usd_low }}–{{ intake.result.estimated_cost_usd_high }} USD)
            · {{ intake.result.estimated_results_low }}–{{ intake.result.estimated_results_high }} Firmen
          </div>
          <div class="text-gray-500">
            Steppe jetzt durch den Wizard und passe Felder an, wenn nötig.
          </div>
        </div>
        <div
          v-if="intake.result?.needs_more_input && intake.result.improvement_hints"
          class="rounded-lg border border-amber-300 bg-amber-50 p-3 text-xs dark:border-amber-700 dark:bg-amber-900/30"
        >
          <div class="font-medium text-amber-900 dark:text-amber-200">
            💡 Beschreibung könnte präziser sein
          </div>
          <p class="mt-1 whitespace-pre-line text-amber-800 dark:text-amber-100">
            {{ intake.result.improvement_hints }}
          </p>
          <p class="mt-1 text-amber-700 dark:text-amber-300">
            Ergänze die Beschreibung oben und drücke nochmal „Vorschlag erzeugen“ —
            der Wizard wird dann mit besseren Vorschlägen befüllt.
          </p>
        </div>
      </div>
    </section>

    <!-- WIZARD MODE -->
    <section
      v-if="mode === 'wizard'"
      class="space-y-4 rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800"
    >
      <!-- Stepper -->
      <div class="flex items-center gap-2 text-xs">
        <div
          v-for="n in 6"
          :key="n"
          :class="[
            'flex h-7 w-7 items-center justify-center rounded-full font-semibold',
            wizardStep === n
              ? 'bg-go4-primary text-white'
              : wizardStep > n
                ? 'bg-green-500 text-white'
                : 'bg-gray-200 text-gray-500 dark:bg-gray-700 dark:text-gray-400'
          ]"
        >
          {{ n }}
        </div>
      </div>

      <!-- Step 1: Datenquelle -->
      <div
        v-if="wizardStep === 1"
        class="space-y-3"
      >
        <h3 class="text-lg font-semibold">
          Datenquelle
        </h3>
        <p class="text-sm text-gray-600 dark:text-gray-400">
          Wähle die Quelle für die Firmensuche.
        </p>
        <label class="flex gap-3 rounded-lg border-2 border-go4-primary p-4 cursor-pointer">
          <input
            v-model="form.source"
            type="radio"
            value="google_places"
            class="mt-1"
          >
          <div>
            <div class="font-medium">Google Places (Maps)</div>
            <div class="text-sm text-gray-600 dark:text-gray-400">
              Firmen mit Google-Business-Profil — 85-95% Handwerk, 50-70% B2B.
              Beste Quelle für lokale Handwerksbetriebe.
            </div>
          </div>
        </label>
      </div>

      <!-- Step 2: Suchmethode -->
      <div
        v-if="wizardStep === 2"
        class="space-y-3"
      >
        <h3 class="text-lg font-semibold">
          Suchmethode
        </h3>
        <p class="text-sm text-gray-600 dark:text-gray-400">
          Wie soll gesucht werden? Mindestens eine Methode auswählen.
        </p>
        <label class="flex gap-3 rounded-lg border border-gray-300 p-4 cursor-pointer dark:border-gray-600">
          <input
            v-model="form.source_config.search_modes.nearby"
            type="checkbox"
            class="mt-1"
          >
          <div>
            <div class="font-medium">Kategorie-Suche (Google Place Types)</div>
            <div class="text-sm text-gray-600 dark:text-gray-400">
              Präzise, aber nur für Standard-Branchen wie electrician, plumber, dentist, …
            </div>
          </div>
        </label>
        <label class="flex gap-3 rounded-lg border border-gray-300 p-4 cursor-pointer dark:border-gray-600">
          <input
            v-model="form.source_config.search_modes.text"
            type="checkbox"
            class="mt-1"
          >
          <div>
            <div class="font-medium">Freitext-Suche (Synonyme)</div>
            <div class="text-sm text-gray-600 dark:text-gray-400">
              Fängt Betriebe ab, die Google nicht kategorisiert hat. Teurer, aber breitere Abdeckung.
            </div>
          </div>
        </label>
      </div>

      <!-- Step 3: Suchparameter prüfen -->
      <div
        v-if="wizardStep === 3"
        class="space-y-3"
      >
        <h3 class="text-lg font-semibold">
          Suchparameter prüfen
        </h3>
        <p class="text-sm text-gray-600 dark:text-gray-400">
          Wenn du den KI-Vorschlag oben genutzt hast, sind Typen und Synonyme schon gefüllt.
          Du kannst hier noch ergänzen, entfernen oder austauschen.
        </p>

        <div
          v-if="intake.result"
          class="rounded-lg bg-blue-50 dark:bg-blue-900/30 p-3 text-xs space-y-1"
        >
          <div><strong>KI-Begründung:</strong> {{ intake.result.reasoning }}</div>
          <div>
            <strong>Erwartet:</strong>
            {{ intake.result.estimated_calls_low }}–{{ intake.result.estimated_calls_high }} Calls,
            ${{ intake.result.estimated_cost_usd_low }}–${{ intake.result.estimated_cost_usd_high }},
            {{ intake.result.estimated_results_low }}–{{ intake.result.estimated_results_high }} Firmen
          </div>
        </div>

        <!-- Editable results: nearby types -->
        <div v-if="form.source_config.search_modes.nearby">
          <label class="block text-sm font-medium mb-1 mt-4">Google Place Types</label>
          <div class="flex flex-wrap gap-2 mb-2">
            <span
              v-for="t in form.source_config.nearby_types"
              :key="t"
              class="inline-flex items-center gap-1 rounded-full bg-blue-100 dark:bg-blue-900/50 px-3 py-1 text-xs"
            >
              {{ t }}
              <button
                type="button"
                class="text-blue-600 hover:text-red-600"
                @click="removeType(t)"
              >×</button>
            </span>
            <span
              v-if="!form.source_config.nearby_types.length"
              class="text-xs text-gray-500"
            >keine gewählt</span>
          </div>
          <select
            class="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700"
            @change="(e) => { addType(e.target.value); e.target.value = '' }"
          >
            <option value="">
              + Type hinzufügen
            </option>
            <option
              v-for="t in supportedTypes"
              :key="t"
              :value="t"
            >
              {{ t }}
            </option>
          </select>
        </div>

        <!-- Editable results: text synonyms -->
        <div v-if="form.source_config.search_modes.text">
          <label class="block text-sm font-medium mb-1 mt-4">Freitext-Synonyme</label>
          <div class="flex flex-wrap gap-2 mb-2">
            <span
              v-for="s in form.source_config.text_synonyms"
              :key="s"
              class="inline-flex items-center gap-1 rounded-full bg-green-100 dark:bg-green-900/50 px-3 py-1 text-xs"
            >
              {{ s }}
              <button
                type="button"
                class="text-green-700 hover:text-red-600"
                @click="removeSynonym(s)"
              >×</button>
            </span>
            <span
              v-if="!form.source_config.text_synonyms.length"
              class="text-xs text-gray-500"
            >keine gewählt</span>
          </div>
          <div class="flex gap-2">
            <input
              id="syn-input"
              type="text"
              placeholder="z.B. Elektroinstallation"
              class="flex-1 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700"
              @keyup.enter="addSynonym"
            >
            <button
              type="button"
              class="rounded-lg border border-gray-300 px-3 py-2 text-sm hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-700"
              @click="addSynonym"
            >
              +
            </button>
          </div>
        </div>
      </div>

      <!-- Step 4: Geografie -->
      <div
        v-if="wizardStep === 4"
        class="space-y-3"
      >
        <h3 class="text-lg font-semibold">
          Geografischer Bereich
        </h3>
        <label class="flex gap-3 rounded-lg border border-gray-300 p-3 cursor-pointer dark:border-gray-600">
          <input
            v-model="form.source_config.geographic.mode"
            type="radio"
            value="germany"
          >
          <div>
            <div class="font-medium">Deutschland komplett</div>
            <div class="text-sm text-gray-600 dark:text-gray-400">Adaptive Kacheln — 800-1500 Calls.</div>
          </div>
        </label>
        <label class="flex gap-3 rounded-lg border border-gray-300 p-3 cursor-pointer dark:border-gray-600">
          <input
            v-model="form.source_config.geographic.mode"
            type="radio"
            value="bundesland"
          >
          <div class="flex-1">
            <div class="font-medium">Ein Bundesland</div>
            <select
              v-if="form.source_config.geographic.mode === 'bundesland'"
              v-model="form.source_config.geographic.bundesland"
              class="mt-2 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700"
            >
              <option :value="null">— wählen —</option>
              <option
                v-for="[key, label] in bundeslaender"
                :key="key"
                :value="key"
              >{{ label }}</option>
            </select>
          </div>
        </label>
        <label class="flex gap-3 rounded-lg border border-gray-300 p-3 cursor-pointer dark:border-gray-600">
          <input
            v-model="form.source_config.geographic.mode"
            type="radio"
            value="circle"
          >
          <div class="flex-1">
            <div class="font-medium">Umkreis um Koordinaten</div>
            <div
              v-if="form.source_config.geographic.mode === 'circle'"
              class="mt-2 grid grid-cols-3 gap-2"
            >
              <input
                v-model.number="form.source_config.geographic.center_lat"
                type="number"
                step="0.0001"
                placeholder="Breitengrad"
                class="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700"
              >
              <input
                v-model.number="form.source_config.geographic.center_lng"
                type="number"
                step="0.0001"
                placeholder="Längengrad"
                class="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700"
              >
              <input
                v-model.number="form.source_config.geographic.radius_km"
                type="number"
                min="1"
                max="500"
                placeholder="Radius km"
                class="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700"
              >
            </div>
          </div>
        </label>
      </div>

      <!-- Step 5: Budget + Pipeline -->
      <div
        v-if="wizardStep === 5"
        class="space-y-4"
      >
        <h3 class="text-lg font-semibold">
          Budget und Engagement-Pipeline
        </h3>
        <div>
          <label class="block text-sm font-medium mb-1">
            Max. API-Calls (Hard-Limit)
          </label>
          <input
            v-model.number="form.source_config.max_api_calls"
            type="number"
            min="1"
            max="100000"
            class="w-40 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700"
          >
          <p class="mt-1 text-xs text-gray-500">
            Bei Überschreitung wird der Run pausiert.
          </p>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">
            Min. Tile-Kantenlänge ({{ form.source_config.min_tile_km }} km)
          </label>
          <input
            v-model.number="form.source_config.min_tile_km"
            type="range"
            min="1"
            max="100"
            class="w-full"
          >
          <p class="mt-1 text-xs text-gray-500">
            Klein = gründlicher, teurer. Groß = günstiger, verliert Detail in Ballungsräumen.
          </p>
        </div>
        <div class="rounded-lg bg-gray-50 dark:bg-gray-900/50 p-4 text-sm">
          <div class="font-medium">
            Kosten-Obergrenze
          </div>
          <div class="mt-1 text-gray-600 dark:text-gray-400">
            Max. {{ costPreview.calls }} Calls × $0.032 ≈ <strong>${{ costPreview.usd }}</strong>
          </div>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Engagement-Pipeline</label>
          <select
            v-model="form.target_engagement_pipeline_id"
            class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700"
          >
            <option :value="null">
              — keine —
            </option>
            <option
              v-for="p in engagement.pipelines"
              :key="p.id"
              :value="p.id"
            >
              {{ p.name }} ({{ p.slug }})
            </option>
          </select>
          <label
            v-if="!isEdit && !form.target_engagement_pipeline_id"
            class="mt-2 flex items-center gap-2 text-sm"
          >
            <input
              v-model="form.create_new_pipeline"
              type="checkbox"
            >
            Neue Engagement-Pipeline automatisch anlegen (channels=letter,email)
          </label>
        </div>
      </div>

      <!-- Step 6: LLM-Analyse / Zielprofil -->
      <div
        v-if="wizardStep === 6"
        class="space-y-4"
      >
        <h3 class="text-lg font-semibold">
          Anreicherungs-Pipeline
        </h3>

        <div class="space-y-2">
          <label class="block text-sm font-medium">Pipeline-Modus</label>
          <div class="space-y-2">
            <label class="flex items-start gap-2 rounded-lg border border-gray-200 p-3 cursor-pointer dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700/50">
              <input
                v-model="form.source_config.pipeline_mode"
                type="radio"
                value="smart"
                class="mt-1"
              >
              <span>
                <span class="font-medium">Smart (empfohlen)</span>
                <span class="block text-xs text-gray-500">
                  Places → LLM. LLM holt Homepages und extrahiert Impressum + Analyse in einem Rutsch.
                  Saubere Geschäftsführer-Namen, ~70% Quote, ca. €0.003/Place.
                </span>
              </span>
            </label>
            <label class="flex items-start gap-2 rounded-lg border border-gray-200 p-3 cursor-pointer dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700/50">
              <input
                v-model="form.source_config.pipeline_mode"
                type="radio"
                value="cheap"
                class="mt-1"
              >
              <span>
                <span class="font-medium">Spar-Modus</span>
                <span class="block text-xs text-gray-500">
                  Places → Regex-Impressum. Kein LLM, 0 € Anreicherungskosten.
                  Aber: nur ~30% saubere Geschäftsführer, keine Relevanz-Bewertung.
                </span>
              </span>
            </label>
            <label class="flex items-start gap-2 rounded-lg border border-gray-200 p-3 cursor-pointer dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700/50">
              <input
                v-model="form.source_config.pipeline_mode"
                type="radio"
                value="legacy"
                class="mt-1"
              >
              <span>
                <span class="font-medium">Doppelt</span>
                <span class="block text-xs text-gray-500">
                  Places → Regex → LLM. Doppelte HTTP-Calls aber Regex als Pre-Filter.
                  Nur wählen wenn du beide Datenstände vergleichen willst.
                </span>
              </span>
            </label>
          </div>
        </div>

        <hr class="border-gray-200 dark:border-gray-700">

        <h4 class="text-md font-semibold">
          LLM-Konfiguration
        </h4>
        <p class="text-xs text-gray-500">
          Nur relevant wenn der Modus LLM einbezieht (Smart oder Doppelt).
          Beschreibe dein Beuteschema und was im Output stehen soll.
        </p>
        <div>
          <label class="block text-sm font-medium mb-1">
            Ziel-Profil (Beuteschema)
          </label>
          <textarea
            v-model="form.source_config.llm.target_profile"
            rows="8"
            placeholder="ZIELGRUPPE: …&#10;MUSS: …&#10;SOLL: …&#10;NICE-TO-HAVE: …&#10;Tonalität: …"
            class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 font-mono text-xs dark:border-gray-600 dark:bg-gray-700"
          />
          <p class="mt-1 text-xs text-gray-500">
            Wonach das LLM suchen soll (welche Firmen passen rein).
          </p>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">
            Was soll das LLM extrahieren? (Output-Spec)
          </label>
          <textarea
            v-model="form.source_config.llm.output_description"
            rows="4"
            placeholder="z.B. Kurze Zusammenfassung der Tätigkeiten, Hinweise auf Wallbox-Erfahrung und Installationskapazität, Mitarbeiterzahl wenn erkennbar, individuelle Ansprache-Idee"
            class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700"
          />
          <p class="mt-1 text-xs text-gray-500">
            Was du im Output erwartest. Wird zusätzlich zum Default-Schema (Score, Services, Marken, Hook etc.) verwendet.
          </p>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">
            LLM-Modell
          </label>
          <select
            v-model="form.source_config.llm.model"
            class="w-64 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700"
          >
            <option value="claude-haiku-4-5">
              Claude Haiku 4.5 (Cloud, ~3¢/Place)
            </option>
            <option value="qwen3:32b">
              Qwen 3 32B (lokal, kostenfrei)
            </option>
          </select>
          <p class="mt-1 text-xs text-gray-500">
            Haiku ist schneller, Qwen 3 läuft lokal auf der DGX und kostet nichts.
          </p>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-sm font-medium mb-1">
              Max. Prospects pro Run
            </label>
            <input
              v-model.number="form.source_config.llm.max_places_per_run"
              type="number"
              min="1"
              max="100000"
              class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700"
            >
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">
              Parallele Requests
            </label>
            <input
              v-model.number="form.source_config.llm.max_concurrency"
              type="number"
              min="1"
              max="20"
              class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700"
            >
          </div>
        </div>
        <details class="rounded-lg border border-gray-200 dark:border-gray-600 p-3">
          <summary class="cursor-pointer text-sm font-medium">
            Prompt-Template anpassen (optional — Default wird verwendet wenn leer)
          </summary>
          <textarea
            v-model="form.source_config.llm.prompt_template"
            rows="10"
            class="mt-2 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 font-mono text-xs dark:border-gray-600 dark:bg-gray-700"
            placeholder="Muss die Platzhalter {target_profile} und {content} enthalten."
          />
          <p class="mt-1 text-xs text-gray-500">
            Muss {target_profile} und {content} enthalten. Lass es leer für den Default.
          </p>
        </details>
        <div class="rounded-lg bg-gray-50 dark:bg-gray-900/50 p-4 text-sm">
          <div class="font-medium">
            Kosten-Schätzung
          </div>
          <div class="mt-1 text-gray-600 dark:text-gray-400">
            Haiku: ca. $0.003/Place × {{ form.source_config.llm.max_places_per_run }} =
            <strong>~${{ (form.source_config.llm.max_places_per_run * 0.003).toFixed(2) }}</strong>
          </div>
        </div>
      </div>

      <!-- Wizard navigation -->
      <div class="flex items-center justify-between pt-4 border-t border-gray-200 dark:border-gray-700">
        <button
          type="button"
          :disabled="wizardStep === 1"
          class="rounded-lg border border-gray-300 px-4 py-2 text-sm disabled:opacity-40 hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-700"
          @click="goPrev"
        >
          ← Zurück
        </button>
        <span class="text-sm text-gray-500">Schritt {{ wizardStep }} von 6</span>
        <button
          v-if="wizardStep < 6"
          type="button"
          class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white"
          @click="goNext"
        >
          Weiter →
        </button>
        <button
          v-else
          type="button"
          :disabled="saving || !canStartRun"
          class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
          @click="save"
        >
          {{ saving ? 'Speichere…' : isEdit ? 'Speichern' : 'Anlegen' }}
        </button>
      </div>
    </section>

    <!-- EXPERT MODE -->
    <form
      v-else
      class="space-y-4 rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800"
      @submit.prevent="save"
    >
      <h3 class="text-lg font-semibold">
        Suche (Google Place Types + Freitext-Synonyme)
      </h3>
      <div class="grid grid-cols-2 gap-4">
        <label class="flex items-center gap-2 text-sm">
          <input
            v-model="form.source_config.search_modes.nearby"
            type="checkbox"
          >
          Kategorie-Suche aktivieren
        </label>
        <label class="flex items-center gap-2 text-sm">
          <input
            v-model="form.source_config.search_modes.text"
            type="checkbox"
          >
          Freitext-Suche aktivieren
        </label>
      </div>
      <div>
        <label class="block text-sm font-medium mb-1">Google Place Types (kommasepariert)</label>
        <input
          :value="form.source_config.nearby_types.join(', ')"
          type="text"
          placeholder="electrician, plumber"
          class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-mono dark:border-gray-600 dark:bg-gray-700"
          @change="(e) => form.source_config.nearby_types = e.target.value.split(',').map(s => s.trim()).filter(Boolean)"
        >
      </div>
      <div>
        <label class="block text-sm font-medium mb-1">Freitext-Synonyme (kommasepariert)</label>
        <input
          :value="form.source_config.text_synonyms.join(', ')"
          type="text"
          placeholder="Elektroinstallation, Elektrotechnik"
          class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-mono dark:border-gray-600 dark:bg-gray-700"
          @change="(e) => form.source_config.text_synonyms = e.target.value.split(',').map(s => s.trim()).filter(Boolean)"
        >
      </div>
      <div class="grid grid-cols-4 gap-3">
        <div>
          <label class="block text-sm font-medium mb-1">Scope</label>
          <select
            v-model="form.source_config.geographic.mode"
            class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700"
          >
            <option value="germany">
              Deutschland
            </option>
            <option value="bundesland">
              Bundesland
            </option>
            <option value="circle">
              Umkreis
            </option>
            <option value="austria">
              Österreich
            </option>
            <option value="switzerland">
              Schweiz
            </option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Max. Calls</label>
          <input
            v-model.number="form.source_config.max_api_calls"
            type="number"
            min="1"
            class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700"
          >
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Min. Tile km</label>
          <input
            v-model.number="form.source_config.min_tile_km"
            type="number"
            min="1"
            max="200"
            class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700"
          >
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Match-Schwelle</label>
          <input
            v-model.number="form.target_match_threshold"
            type="number"
            min="0"
            max="10"
            class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700"
          >
        </div>
      </div>

      <h3 class="text-lg font-semibold pt-2 border-t border-gray-200 dark:border-gray-700">
        Anreicherungs-Pipeline (Stage 2 + 3)
      </h3>
      <div>
        <label class="block text-sm font-medium mb-1">Pipeline-Modus</label>
        <select
          v-model="form.source_config.pipeline_mode"
          class="w-64 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700"
        >
          <option value="smart">
            Smart (Places → LLM, empfohlen)
          </option>
          <option value="cheap">
            Spar-Modus (Places → Regex-Impressum)
          </option>
          <option value="legacy">
            Doppelt (Places → Regex → LLM)
          </option>
        </select>
      </div>
      <div>
        <label class="block text-sm font-medium mb-1">
          Ziel-Profil / Beuteschema
          <span class="ml-1 text-xs font-normal text-gray-500">
            — wird Stage 3 als Match-Kriterium übergeben
          </span>
        </label>
        <textarea
          v-model="form.source_config.llm.target_profile"
          rows="14"
          placeholder="ZIELGRUPPE: …&#10;MUSS-KRITERIEN: …&#10;SOLL-KRITERIEN: …&#10;NICE-TO-HAVE: …&#10;ROTE FLAGGEN: …&#10;ANSPRACHE-TONALITÄT: …"
          class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 font-mono text-xs dark:border-gray-600 dark:bg-gray-700"
        />
      </div>
      <div>
        <label class="block text-sm font-medium mb-1">
          Output-Spec
          <span class="ml-1 text-xs font-normal text-gray-500">
            — was Stage 3 fürs nachgelagerte Mail-Modul liefert
          </span>
        </label>
        <textarea
          v-model="form.source_config.llm.output_description"
          rows="14"
          placeholder="KONTAKTPERSON …&#10;PRE-PITCH-INTEL …&#10;ATOMARE FELDER …"
          class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 font-mono text-xs dark:border-gray-600 dark:bg-gray-700"
        />
      </div>
      <div class="grid grid-cols-3 gap-3">
        <div>
          <label class="block text-sm font-medium mb-1">LLM-Modell</label>
          <select
            v-model="form.source_config.llm.model"
            class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700"
          >
            <option value="claude-haiku-4-5">
              Haiku 4.5 (Cloud)
            </option>
            <option value="qwen3:32b">
              Qwen 3 32B (lokal)
            </option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Max. Prospects / Run</label>
          <input
            v-model.number="form.source_config.llm.max_places_per_run"
            type="number"
            min="1"
            max="100000"
            class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700"
          >
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Parallele Requests</label>
          <input
            v-model.number="form.source_config.llm.max_concurrency"
            type="number"
            min="1"
            max="20"
            class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700"
          >
        </div>
      </div>
      <details class="rounded-lg border border-gray-200 dark:border-gray-600 p-3">
        <summary class="cursor-pointer text-sm font-medium">
          Prompt-Template anpassen (optional — Default wird verwendet wenn leer)
        </summary>
        <textarea
          v-model="form.source_config.llm.prompt_template"
          rows="14"
          class="mt-2 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 font-mono text-xs dark:border-gray-600 dark:bg-gray-700"
          placeholder="Muss die Platzhalter {target_profile}, {output_description} und {content} enthalten."
        />
        <p class="mt-1 text-xs text-gray-500">
          Muss die Platzhalter <code>{target_profile}</code>, <code>{output_description}</code>
          und <code>{content}</code> enthalten. Lass es leer für den Default.
        </p>
      </details>

      <h3 class="text-lg font-semibold pt-2 border-t border-gray-200 dark:border-gray-700">
        Engagement-Handoff
      </h3>
      <div>
        <label class="block text-sm font-medium mb-1">Engagement-Pipeline</label>
        <select
          v-model="form.target_engagement_pipeline_id"
          class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700"
        >
          <option :value="null">
            — keine —
          </option>
          <option
            v-for="p in engagement.pipelines"
            :key="p.id"
            :value="p.id"
          >
            {{ p.name }} ({{ p.slug }})
          </option>
        </select>
        <label
          v-if="!isEdit && !form.target_engagement_pipeline_id"
          class="mt-2 flex items-center gap-2 text-sm"
        >
          <input
            v-model="form.create_new_pipeline"
            type="checkbox"
          >
          Neue Engagement-Pipeline automatisch anlegen
        </label>
      </div>

      <div
        v-if="localError"
        class="rounded-lg bg-red-50 p-3 text-sm text-red-700"
      >
        {{ localError }}
      </div>

      <div class="flex gap-3 pt-2">
        <button
          type="submit"
          :disabled="saving"
          class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
        >
          {{ saving ? 'Speichere…' : isEdit ? 'Speichern' : 'Anlegen' }}
        </button>
        <button
          type="button"
          class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-700"
          @click="cancel"
        >
          Abbrechen
        </button>
      </div>
    </form>

    <!-- Error banner for wizard -->
    <div
      v-if="localError && mode === 'wizard'"
      class="rounded-lg bg-red-50 p-3 text-sm text-red-700"
    >
      {{ localError }}
    </div>

    <div
      v-if="mode === 'wizard'"
      class="flex justify-end"
    >
      <button
        type="button"
        class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-700"
        @click="cancel"
      >
        Abbrechen
      </button>
    </div>
  </div>
</template>
