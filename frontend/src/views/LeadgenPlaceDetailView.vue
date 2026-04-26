<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLeadgenStore } from '@/stores/leadgen'
import PageHeader from '@/components/ui/PageHeader.vue'

const props = defineProps({
  id: { type: [String, Number], default: null }
})

const route = useRoute()
const router = useRouter()
const store = useLeadgenStore()

const placeId = computed(() => props.id || route.params.id)
const showRejectForm = ref(false)
const rejectReason = ref('')
const working = ref(false)
const localError = ref(null)

onMounted(async () => {
  await store.fetchPlace(placeId.value)
})

const place = computed(() => store.currentPlace)

async function confirmReject() {
  if (!rejectReason.value.trim()) return
  working.value = true
  localError.value = null
  try {
    await store.rejectPlaceAction(placeId.value, rejectReason.value.trim())
    await store.fetchPlace(placeId.value)
    showRejectForm.value = false
    rejectReason.value = ''
  } catch (e) {
    localError.value = e.response?.data?.detail || e.message
  } finally {
    working.value = false
  }
}
</script>

<template>
  <div class="p-6 space-y-4 max-w-4xl">
    <div v-if="place">
      <PageHeader :title="place.name" :subtitle="place.formatted_address || ''" />

      <div class="flex items-center gap-3 mt-3">
        <span class="inline-flex px-2 py-0.5 text-xs font-medium rounded bg-gray-100 text-gray-700">
          Status: {{ place.status }}
        </span>
        <span v-if="place.rejected_reason" class="text-sm text-red-600">
          Abgelehnt: {{ place.rejected_reason }}
        </span>
        <button
          v-if="place.status !== 'rejected'"
          class="ml-auto rounded-lg border border-red-300 px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50"
          @click="showRejectForm = true"
        >
          Ablehnen
        </button>
        <button class="text-sm text-gray-500 hover:underline" @click="router.back()">Zurück</button>
      </div>

      <div v-if="showRejectForm" class="mt-3 rounded-lg border border-red-200 bg-red-50 p-3">
        <label class="block text-sm font-medium mb-1">Ablehnungsgrund</label>
        <input
          v-model="rejectReason"
          type="text"
          placeholder="z.B. Kein PV-Bezug"
          class="w-full rounded border border-red-300 bg-white px-3 py-1.5 text-sm"
        />
        <div class="mt-2 flex gap-2">
          <button
            :disabled="working || !rejectReason.trim()"
            class="rounded bg-red-600 px-3 py-1 text-sm text-white disabled:opacity-60"
            @click="confirmReject"
          >
            Bestätigen
          </button>
          <button class="text-sm text-gray-500 hover:underline" @click="showRejectForm = false">
            Abbrechen
          </button>
        </div>
        <p v-if="localError" class="mt-2 text-sm text-red-700">
          {{ localError }}
        </p>
      </div>

      <div
        class="mt-6 rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
      >
        <h3 class="text-sm font-semibold mb-3">Kontakt & Adresse</h3>
        <dl class="grid grid-cols-2 gap-x-6 gap-y-1 text-sm">
          <dt class="text-gray-500">Name</dt>
          <dd>{{ place.name }}</dd>
          <dt class="text-gray-500">Strasse</dt>
          <dd>{{ place.address_street || '-' }}</dd>
          <dt class="text-gray-500">PLZ</dt>
          <dd>{{ place.address_zip || '-' }}</dd>
          <dt class="text-gray-500">Stadt</dt>
          <dd>{{ place.address_city || '-' }}</dd>
          <dt class="text-gray-500">Website</dt>
          <dd>
            <a
              v-if="place.website"
              :href="place.website"
              target="_blank"
              rel="noopener"
              class="text-go4-primary hover:underline"
              >{{ place.website }}</a
            >
            <span v-else>-</span>
          </dd>
          <dt class="text-gray-500">Telefon</dt>
          <dd>{{ place.phone || '-' }}</dd>
          <dt class="text-gray-500">Bewertung</dt>
          <dd>{{ place.rating || '-' }} ({{ place.user_ratings_total || 0 }})</dd>
          <dt class="text-gray-500">Business Status</dt>
          <dd>{{ place.business_status || '-' }}</dd>
          <dt class="text-gray-500">Google-ID</dt>
          <dd class="font-mono text-xs">
            {{ place.google_place_id }}
          </dd>
        </dl>
      </div>

      <div
        v-if="!place.impressum && !place.llm_insights"
        class="mt-4 rounded-lg border border-dashed border-gray-300 bg-gray-50 p-4 text-sm dark:border-gray-600 dark:bg-gray-900/40"
      >
        <div class="font-medium text-gray-800 dark:text-gray-200">
          Noch nicht angereichert
        </div>
        <p class="mt-1 text-gray-600 dark:text-gray-400">
          Dieser Prospect wurde von Google Places gefunden (Status:
          <code class="rounded bg-gray-200 px-1 py-0.5 text-xs dark:bg-gray-700">{{ place.status }}</code>),
          aber Impressum &amp; LLM-Analyse wurden noch nicht ausgeführt. Starte einen
          Anreicherungs-Run auf der Kampagnen-Detail-Seite, um diese Daten zu erzeugen.
        </p>
        <router-link
          :to="`/leadgen/campaigns/${place.campaign_id}`"
          class="mt-3 inline-flex items-center text-sm font-medium text-go4-primary hover:underline"
        >
          → Zur Kampagne
        </router-link>
      </div>

      <div
        v-if="place.impressum"
        class="mt-4 rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
      >
        <h3 class="text-sm font-semibold mb-3">Impressum-Daten (Stage 2)</h3>
        <dl v-if="!place.impressum.extraction_error" class="grid grid-cols-3 gap-x-4 gap-y-2 text-sm">
          <dt class="text-gray-500">Email</dt>
          <dd class="col-span-2">
            <a
              v-if="place.impressum.email"
              :href="`mailto:${place.impressum.email}`"
              class="text-go4-primary hover:underline"
            >{{ place.impressum.email }}</a>
            <span v-else class="text-gray-400">-</span>
          </dd>
          <dt class="text-gray-500">Telefon</dt>
          <dd class="col-span-2">{{ place.impressum.phone || '-' }}</dd>
          <dt class="text-gray-500">Geschäftsführung</dt>
          <dd class="col-span-2">
            <span v-if="place.impressum.managing_directors?.length">
              {{ place.impressum.managing_directors.join(', ') }}
            </span>
            <span v-else class="text-gray-400">-</span>
          </dd>
          <dt class="text-gray-500">Postanschrift</dt>
          <dd class="col-span-2">{{ place.impressum.postal_address || '-' }}</dd>
          <dt class="text-gray-500">Handelsregister</dt>
          <dd class="col-span-2">{{ place.impressum.handelsregister || '-' }}</dd>
          <dt class="text-gray-500">USt-IdNr.</dt>
          <dd class="col-span-2">{{ place.impressum.ust_id || '-' }}</dd>
          <dt class="text-gray-500">Quelle</dt>
          <dd class="col-span-2">
            <a
              v-if="place.impressum.source_url"
              :href="place.impressum.source_url"
              target="_blank"
              rel="noopener"
              class="text-go4-primary hover:underline break-all"
            >{{ place.impressum.source_url }}</a>
            <span v-else class="text-gray-400">-</span>
          </dd>
          <dt class="text-gray-500">Extrahiert am</dt>
          <dd class="col-span-2 text-gray-500">
            {{ place.impressum.extracted_at ? new Date(place.impressum.extracted_at).toLocaleString('de-DE') : '-' }}
          </dd>
        </dl>
        <p v-else class="rounded-lg bg-red-50 p-2 text-sm text-red-700">
          Scraping fehlgeschlagen: {{ place.impressum.extraction_error }}
        </p>
      </div>

      <div
        v-if="place.llm_insights"
        class="mt-4 rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
      >
        <h3 class="text-sm font-semibold mb-3">
          LLM-Analyse (Stage 3) ·
          <span v-if="place.llm_insights.target_match_score != null"
            class="inline-flex items-center rounded-full px-2 py-0.5 text-xs"
            :class="place.llm_insights.target_match_score >= 7 ? 'bg-green-100 text-green-800' : place.llm_insights.target_match_score >= 4 ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800'"
          >
            Match {{ place.llm_insights.target_match_score }}/10
          </span>
        </h3>
        <div
          v-if="place.llm_insights.primary_contact && (place.llm_insights.primary_contact.first_name || place.llm_insights.primary_contact.last_name)"
          class="mb-3 rounded-lg bg-blue-50 dark:bg-blue-900/30 p-3 text-sm"
        >
          <div class="text-xs font-medium uppercase text-blue-900 dark:text-blue-200">
            Primärer Kontakt
          </div>
          <div class="mt-1 text-gray-800 dark:text-gray-100">
            <span v-if="place.llm_insights.primary_contact.salutation">{{ place.llm_insights.primary_contact.salutation }} </span>
            <span class="font-medium">
              {{ place.llm_insights.primary_contact.first_name }}
              {{ place.llm_insights.primary_contact.last_name }}
            </span>
            <span
              v-if="place.llm_insights.primary_contact.role"
              class="text-gray-600 dark:text-gray-400"
            > · {{ place.llm_insights.primary_contact.role }}</span>
          </div>
          <div class="mt-0.5 text-xs text-gray-500">
            <span v-if="place.llm_insights.primary_contact.gender">Geschlecht: {{ place.llm_insights.primary_contact.gender }}</span>
            <span v-if="place.llm_insights.primary_contact.source"> · Quelle: {{ place.llm_insights.primary_contact.source }}</span>
          </div>
        </div>
        <div v-if="place.llm_insights.extraction_error" class="rounded-lg bg-red-50 p-2 text-sm text-red-700">
          Analyse fehlgeschlagen: {{ place.llm_insights.extraction_error }}
        </div>
        <dl v-else class="grid grid-cols-3 gap-x-4 gap-y-2 text-sm">
          <dt class="text-gray-500">Pre-Pitch-Intel</dt>
          <dd class="col-span-2 whitespace-pre-line text-gray-700 dark:text-gray-300">
            {{ place.llm_insights.personalization_hook || '-' }}
          </dd>
          <dt class="text-gray-500">Firmengröße</dt>
          <dd class="col-span-2">{{ place.llm_insights.company_size_indicator || '-' }}</dd>
          <dt class="text-gray-500">Dienstleistungen</dt>
          <dd class="col-span-2">
            <span v-if="place.llm_insights.services?.length" class="flex flex-wrap gap-1">
              <span
                v-for="(s, i) in place.llm_insights.services"
                :key="i"
                class="rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-800"
              >{{ s }}</span>
            </span>
            <span v-else>-</span>
          </dd>
          <dt class="text-gray-500">Hersteller/Marken</dt>
          <dd class="col-span-2">
            <span v-if="place.llm_insights.brands?.length">{{ place.llm_insights.brands.join(', ') }}</span>
            <span v-else>-</span>
          </dd>
          <dt class="text-gray-500">Zielsegmente</dt>
          <dd class="col-span-2">
            <span v-if="place.llm_insights.customer_segments?.length">{{ place.llm_insights.customer_segments.join(', ') }}</span>
            <span v-else>-</span>
          </dd>
          <dt class="text-gray-500">Rote Flaggen</dt>
          <dd class="col-span-2">
            <span v-if="place.llm_insights.red_flags?.length" class="flex flex-wrap gap-1">
              <span
                v-for="(f, i) in place.llm_insights.red_flags"
                :key="i"
                class="rounded-full bg-red-100 px-2 py-0.5 text-xs text-red-800"
              >{{ f }}</span>
            </span>
            <span v-else class="text-gray-400">keine</span>
          </dd>
          <dt class="text-gray-500">Analysiert</dt>
          <dd class="col-span-2 text-gray-500">
            {{ place.llm_insights.pages_analyzed?.length || 0 }} Seiten ·
            {{ place.llm_insights.input_tokens || 0 }} in / {{ place.llm_insights.output_tokens || 0 }} out Tokens ·
            {{ place.llm_insights.model_used }} ·
            {{ place.llm_insights.cost_cents ? (place.llm_insights.cost_cents / 100).toFixed(3) + ' €' : '-' }}
          </dd>
          <dt class="text-gray-500">Seiten</dt>
          <dd class="col-span-2 space-y-0.5 text-xs">
            <div v-for="p in place.llm_insights.pages_analyzed" :key="p">
              <a :href="p" target="_blank" rel="noopener" class="text-go4-primary hover:underline break-all">{{ p }}</a>
            </div>
          </dd>
          <dt class="text-gray-500">Extrahiert am</dt>
          <dd class="col-span-2 text-gray-500">
            {{ place.llm_insights.extracted_at ? new Date(place.llm_insights.extracted_at).toLocaleString('de-DE') : '-' }}
          </dd>
        </dl>
      </div>

      <div
        class="mt-4 rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
      >
        <h3 class="text-sm font-semibold mb-3">Handoff</h3>
        <p class="text-sm">
          Kontakt: <span v-if="place.contact_id">#{{ place.contact_id }}</span
          ><span v-else class="text-gray-500">noch nicht angelegt</span>
        </p>
      </div>
    </div>
  </div>
</template>
