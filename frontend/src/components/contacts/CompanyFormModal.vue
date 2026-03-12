<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  company: { type: Object, default: null },
  loading: { type: Boolean, default: false }
})

const emit = defineEmits(['close', 'save'])

const form = ref({
  name: '',
  domain: '',
  website: '',
  industry: '',
  size: '',
  phone: '',
  email: '',
  description: '',
  tags: []
})

const sizeOptions = [
  { value: '1-10', label: '1-10 Mitarbeiter' },
  { value: '11-50', label: '11-50 Mitarbeiter' },
  { value: '51-200', label: '51-200 Mitarbeiter' },
  { value: '201-500', label: '201-500 Mitarbeiter' },
  { value: '500+', label: '500+ Mitarbeiter' }
]

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen && props.company) {
      form.value = {
        name: props.company.name || '',
        domain: props.company.domain || '',
        website: props.company.website || '',
        industry: props.company.industry || '',
        size: props.company.size || '',
        phone: props.company.phone || '',
        email: props.company.email || '',
        description: props.company.description || '',
        tags: props.company.tags || []
      }
    } else if (isOpen) {
      form.value = {
        name: '',
        domain: '',
        website: '',
        industry: '',
        size: '',
        phone: '',
        email: '',
        description: '',
        tags: []
      }
    }
  }
)

function onSubmit() {
  emit('save', { ...form.value })
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      @click.self="emit('close')"
    >
      <div class="w-full max-w-lg rounded-lg bg-white dark:bg-gray-800 shadow-xl">
        <div
          class="flex items-center justify-between border-b border-gray-200 dark:border-gray-700 px-6 py-4"
        >
          <h2 class="text-lg font-semibold text-go4-secondary dark:text-gray-100">
            {{ company ? 'Firma bearbeiten' : 'Neue Firma' }}
          </h2>
          <button
            type="button"
            class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            @click="emit('close')"
          >
            <svg
              class="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <form
          class="p-6 space-y-4"
          @submit.prevent="onSubmit"
        >
          <div class="grid grid-cols-2 gap-4">
            <div class="col-span-2">
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Firmenname *</label>
              <input
                v-model="form.name"
                type="text"
                required
                class="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
                placeholder="ACME GmbH"
              >
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Domain</label>
              <input
                v-model="form.domain"
                type="text"
                class="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
                placeholder="acme.com"
              >
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Website</label>
              <input
                v-model="form.website"
                type="url"
                class="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
                placeholder="https://www.acme.com"
              >
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Branche</label>
              <input
                v-model="form.industry"
                type="text"
                class="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
                placeholder="Software"
              >
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Größe</label>
              <select
                v-model="form.size"
                class="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
              >
                <option value="">
                  Auswählen...
                </option>
                <option
                  v-for="opt in sizeOptions"
                  :key="opt.value"
                  :value="opt.value"
                >
                  {{ opt.label }}
                </option>
              </select>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Telefon</label>
              <input
                v-model="form.phone"
                type="tel"
                class="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
                placeholder="+49 123 456789"
              >
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">E-Mail</label>
              <input
                v-model="form.email"
                type="email"
                class="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
                placeholder="info@acme.com"
              >
            </div>

            <div class="col-span-2">
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Beschreibung</label>
              <textarea
                v-model="form.description"
                rows="3"
                class="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
                placeholder="Kurze Beschreibung der Firma..."
              />
            </div>
          </div>

          <div class="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <button
              type="button"
              class="rounded-lg border border-gray-300 dark:border-gray-600 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
              @click="emit('close')"
            >
              Abbrechen
            </button>
            <button
              type="submit"
              :disabled="loading"
              class="rounded-lg bg-go4-primary px-4 py-2 text-sm font-medium text-white hover:bg-go4-primary-dark disabled:opacity-50"
            >
              {{ loading ? 'Speichert...' : 'Speichern' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>
