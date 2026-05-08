<script setup>
/**
 * Tenant-Stammdaten — Tab-Komponente in SettingsView.
 *
 * Pflichtangaben gemäß §5 TMG für E-Mail-Footer (Impressum, Disclaimer)
 * plus Compliance-Felder (Datenschutz-URL, Test-Empfänger).
 *
 * Live-Preview rechts zeigt den generierten Impressum-HTML wie er im
 * Email-Footer landet — Feedback während des Eintippens.
 */
import { ref, reactive, computed, onMounted, watch } from 'vue'
import {
  getTenantMasterData,
  updateTenantMasterData,
  previewImpressum,
  previewDisclaimer,
} from '@/api/tenantSettings'

const loading = ref(false)
const saving = ref(false)
const error = ref(null)
const successMsg = ref(null)

const form = reactive({
  legal_name: '',
  display_name: '',
  legal_form: '',
  street: '',
  street_number: '',
  postal_code: '',
  city: '',
  country: 'DE',
  phone: '',
  email: '',
  website: '',
  managing_directors_text: '',  // string, splitting on save
  register_court: '',
  register_number: '',
  responsible_for_content: '',
  vat_id: '',
  tax_id: '',
  privacy_url: '',
  imprint_url: '',
  test_recipient_email: '',
  default_disclaimer_html: '',
  unsubscribe_url_base: '',
  impressum_html_override: '',
})

const preview = ref({ impressum_html: '', is_override: false, is_complete: false, missing_fields: [] })
const disclaimerPreview = ref('')

const missingMap = computed(() => new Set(preview.value.missing_fields || []))

async function load() {
  loading.value = true
  error.value = null
  try {
    const { data } = await getTenantMasterData()
    if (data) {
      Object.keys(form).forEach((key) => {
        if (key === 'managing_directors_text') {
          form.managing_directors_text = (data.managing_directors || []).join(', ')
        } else if (key in data && data[key] != null) {
          form[key] = data[key]
        }
      })
    }
    await refreshPreviews()
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    loading.value = false
  }
}

async function refreshPreviews() {
  try {
    const [imp, dis] = await Promise.all([previewImpressum(), previewDisclaimer()])
    preview.value = imp.data
    disclaimerPreview.value = dis.data?.disclaimer_html || ''
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  }
}

async function save() {
  saving.value = true
  error.value = null
  successMsg.value = null
  try {
    const payload = { ...form }
    payload.managing_directors = form.managing_directors_text
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
    delete payload.managing_directors_text
    Object.keys(payload).forEach((k) => {
      if (payload[k] === '') payload[k] = null
    })
    payload.country = form.country || 'DE'
    await updateTenantMasterData(payload)
    successMsg.value = 'Gespeichert.'
    await refreshPreviews()
    setTimeout(() => { successMsg.value = null }, 3000)
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    saving.value = false
  }
}

let saveDebounce = null
watch(form, () => {
  if (saveDebounce) clearTimeout(saveDebounce)
  saveDebounce = setTimeout(refreshPreviews, 500)
}, { deep: true })

onMounted(load)

const fieldLabels = {
  legal_name: 'Firmenname',
  street: 'Straße',
  postal_code: 'PLZ',
  city: 'Stadt',
  phone: 'Telefon',
  email: 'E-Mail',
  managing_directors: 'Vertretung',
  register_court: 'Registergericht',
  register_number: 'Registernummer',
  vat_id: 'USt-IdNr.',
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <p class="text-sm text-gray-500 dark:text-gray-400">
        Pflichtangaben für rechtskonforme E-Mail-Footer (§5 TMG, DSGVO).
      </p>
      <button
        type="button"
        class="rounded-md bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark disabled:opacity-50"
        :disabled="saving"
        @click="save"
      >
        {{ saving ? 'Speichere…' : 'Speichern' }}
      </button>
    </div>

    <div v-if="error" class="rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-300">
      {{ error }}
    </div>
    <div v-if="successMsg" class="rounded-md bg-emerald-50 p-3 text-sm text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-300">
      ✓ {{ successMsg }}
    </div>
    <div v-if="!preview.is_complete && preview.missing_fields.length" class="rounded-md bg-amber-50 p-3 text-sm text-amber-800 dark:bg-amber-900/20 dark:text-amber-300">
      <strong>Pflichtfelder fehlen:</strong>
      {{ preview.missing_fields.map(f => fieldLabels[f] || f).join(', ') }}
    </div>

    <div v-if="loading" class="py-8 text-center text-sm text-gray-500">Lädt…</div>
    <div v-else class="grid grid-cols-1 gap-4 lg:grid-cols-3">
      <!-- Form (left, 2 cols) -->
      <div class="space-y-4 lg:col-span-2">
        <!-- Firma -->
        <section class="rounded-lg bg-white p-5 shadow dark:bg-gray-800">
          <h3 class="mb-3 text-sm font-semibold text-gray-900 dark:text-gray-100">Firma</h3>
          <div class="grid grid-cols-2 gap-3">
            <div class="col-span-2">
              <label class="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">
                Firmenname <span v-if="missingMap.has('legal_name')" class="text-amber-600">*</span>
              </label>
              <input v-model="form.legal_name" type="text" class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100" placeholder="z.B. Smartladen.de GmbH" />
            </div>
            <div>
              <label class="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">Anzeigename</label>
              <input v-model="form.display_name" type="text" class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100" placeholder="z.B. smartladen.de" />
            </div>
            <div>
              <label class="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">Rechtsform</label>
              <select v-model="form.legal_form" class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100">
                <option value="">— wählen —</option>
                <option value="GmbH">GmbH</option>
                <option value="UG">UG (haftungsbeschränkt)</option>
                <option value="AG">AG</option>
                <option value="GbR">GbR</option>
                <option value="OHG">OHG</option>
                <option value="KG">KG</option>
                <option value="GmbH & Co. KG">GmbH &amp; Co. KG</option>
                <option value="Einzelunternehmen">Einzelunternehmen</option>
                <option value="Verein">e.V.</option>
                <option value="Stiftung">Stiftung</option>
              </select>
            </div>
          </div>
        </section>

        <!-- Adresse -->
        <section class="rounded-lg bg-white p-5 shadow dark:bg-gray-800">
          <h3 class="mb-3 text-sm font-semibold text-gray-900 dark:text-gray-100">Adresse</h3>
          <div class="grid grid-cols-6 gap-3">
            <div class="col-span-4">
              <label class="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">
                Straße <span v-if="missingMap.has('street')" class="text-amber-600">*</span>
              </label>
              <input v-model="form.street" type="text" class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100" />
            </div>
            <div class="col-span-2">
              <label class="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">Nr.</label>
              <input v-model="form.street_number" type="text" class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100" />
            </div>
            <div class="col-span-2">
              <label class="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">
                PLZ <span v-if="missingMap.has('postal_code')" class="text-amber-600">*</span>
              </label>
              <input v-model="form.postal_code" type="text" class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100" />
            </div>
            <div class="col-span-3">
              <label class="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">
                Stadt <span v-if="missingMap.has('city')" class="text-amber-600">*</span>
              </label>
              <input v-model="form.city" type="text" class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100" />
            </div>
            <div class="col-span-1">
              <label class="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">Land</label>
              <input v-model="form.country" type="text" maxlength="2" class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100" />
            </div>
          </div>
        </section>

        <!-- Kontakt -->
        <section class="rounded-lg bg-white p-5 shadow dark:bg-gray-800">
          <h3 class="mb-3 text-sm font-semibold text-gray-900 dark:text-gray-100">Kontakt</h3>
          <div class="grid grid-cols-3 gap-3">
            <div>
              <label class="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">
                Telefon <span v-if="missingMap.has('phone')" class="text-amber-600">*</span>
              </label>
              <input v-model="form.phone" type="tel" class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100" />
            </div>
            <div>
              <label class="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">
                E-Mail <span v-if="missingMap.has('email')" class="text-amber-600">*</span>
              </label>
              <input v-model="form.email" type="email" class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100" />
            </div>
            <div>
              <label class="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">Website</label>
              <input v-model="form.website" type="url" placeholder="https://…" class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100" />
            </div>
          </div>
        </section>

        <!-- Vertretung & Register -->
        <section class="rounded-lg bg-white p-5 shadow dark:bg-gray-800">
          <h3 class="mb-3 text-sm font-semibold text-gray-900 dark:text-gray-100">Vertretung &amp; Handelsregister</h3>
          <div class="grid grid-cols-2 gap-3">
            <div class="col-span-2">
              <label class="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">
                Geschäftsführer / Vertretungsberechtigte <span v-if="missingMap.has('managing_directors')" class="text-amber-600">*</span>
              </label>
              <input v-model="form.managing_directors_text" type="text" placeholder="Komma-separiert: Harry Ketschik, Max Mustermann" class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100" />
            </div>
            <div>
              <label class="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">
                Registergericht <span v-if="missingMap.has('register_court')" class="text-amber-600">*</span>
              </label>
              <input v-model="form.register_court" type="text" placeholder="z.B. Würzburg" class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100" />
            </div>
            <div>
              <label class="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">
                Registernummer <span v-if="missingMap.has('register_number')" class="text-amber-600">*</span>
              </label>
              <input v-model="form.register_number" type="text" placeholder="z.B. HRB 12345" class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100" />
            </div>
            <div class="col-span-2">
              <label class="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">Verantwortlich i.S.d. § 55 RStV</label>
              <input v-model="form.responsible_for_content" type="text" placeholder="Falls anders als Geschäftsführer" class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100" />
            </div>
          </div>
        </section>

        <!-- Steuer -->
        <section class="rounded-lg bg-white p-5 shadow dark:bg-gray-800">
          <h3 class="mb-3 text-sm font-semibold text-gray-900 dark:text-gray-100">Steuer</h3>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">
                USt-IdNr. <span v-if="missingMap.has('vat_id')" class="text-amber-600">*</span>
              </label>
              <input v-model="form.vat_id" type="text" placeholder="DE123456789" class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100" />
            </div>
            <div>
              <label class="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">Steuernummer (optional)</label>
              <input v-model="form.tax_id" type="text" class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100" />
            </div>
          </div>
        </section>

        <!-- Compliance -->
        <section class="rounded-lg bg-white p-5 shadow dark:bg-gray-800">
          <h3 class="mb-3 text-sm font-semibold text-gray-900 dark:text-gray-100">Compliance &amp; Tracking</h3>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">Datenschutz-URL</label>
              <input v-model="form.privacy_url" type="url" placeholder="https://…/datenschutz" class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100" />
            </div>
            <div>
              <label class="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">Impressum-URL (Footer-Link)</label>
              <input v-model="form.imprint_url" type="url" placeholder="https://…/impressum" class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100" />
            </div>
            <div class="col-span-2">
              <label class="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">Test-Empfänger E-Mail (für Probesendungen)</label>
              <input v-model="form.test_recipient_email" type="email" placeholder="harry@smartladen.de" class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100" />
            </div>
            <div class="col-span-2">
              <label class="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">
                Custom Unsubscribe-URL (optional)
              </label>
              <input
                v-model="form.unsubscribe_url_base"
                type="url"
                placeholder="z.B. https://smartladen.de/abmelden/"
                class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100"
              />
              <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
                Wenn leer: <code>{{ 'https://automate.go4.energy/api/v1/emailmarketing/t/u/<hash>' }}</code>.
                Wenn gesetzt: Tracking-Hash wird hinten angehängt — die Domain muss
                den Pfad als Reverse-Proxy oder eigene Page bereitstellen.
              </p>
            </div>

            <div class="col-span-2">
              <label class="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">DSGVO-Disclaimer (HTML, optional — sonst Default-Block)</label>
              <textarea v-model="form.default_disclaimer_html" rows="4" class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 font-mono text-xs dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100" />
            </div>
            <div class="col-span-2">
              <label class="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">Impressum-HTML-Override (nur für Sonderfälle)</label>
              <textarea v-model="form.impressum_html_override" rows="4" placeholder="Lass leer — der Block wird automatisch aus den obigen Feldern generiert." class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 font-mono text-xs dark:border-gray-600 dark:bg-gray-900 dark:text-gray-100" />
            </div>
          </div>
        </section>
      </div>

      <!-- Live-Preview rechts -->
      <div class="space-y-4">
        <section class="sticky top-4 rounded-lg bg-white p-5 shadow dark:bg-gray-800">
          <h3 class="mb-3 text-sm font-semibold text-gray-900 dark:text-gray-100">
            🔍 Vorschau: Impressum-Block
            <span v-if="preview.is_override" class="ml-1 rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 dark:bg-amber-900/40 dark:text-amber-300">Override aktiv</span>
            <span v-else-if="preview.is_complete" class="ml-1 rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300">vollständig</span>
            <span v-else class="ml-1 rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 dark:bg-amber-900/40 dark:text-amber-300">unvollständig</span>
          </h3>
          <div class="rounded border border-gray-200 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-900/40">
            <div v-if="preview.impressum_html" v-html="preview.impressum_html" />
            <p v-else class="text-xs italic text-gray-500">Pflichtfelder ausfüllen — der Block wird hier live aufgebaut.</p>
          </div>
          <h3 class="mb-2 mt-5 text-sm font-semibold text-gray-900 dark:text-gray-100">🔍 Vorschau: DSGVO-Disclaimer</h3>
          <div class="rounded border border-gray-200 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-900/40">
            <div v-if="disclaimerPreview" v-html="disclaimerPreview" />
            <p v-else class="text-xs italic text-gray-500">…</p>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>
