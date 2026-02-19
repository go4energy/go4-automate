<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useResearchStore } from '@/stores/research'

const router = useRouter()
const store = useResearchStore()

const saving = ref(false)
const error = ref(null)
const generateAfterSave = ref(false)
const uploadingImage = ref(false)

const form = ref({
  title: '',
  description: '',
  category: 'content',
  platforms: [],
  priority: 3,
  source_type: 'manual',
  image_url: null
})

const generatePlatform = ref('facebook')
const generateType = ref('post')

const platformOptions = [
  { value: 'facebook', label: 'Facebook' },
  { value: 'instagram', label: 'Instagram' },
  { value: 'linkedin', label: 'LinkedIn' },
  { value: 'email', label: 'E-Mail' }
]

function togglePlatform(value) {
  const idx = form.value.platforms.indexOf(value)
  if (idx === -1) {
    form.value.platforms.push(value)
  } else {
    form.value.platforms.splice(idx, 1)
  }
}

async function handleImageUpload(event) {
  const file = event.target.files?.[0]
  if (!file) return

  uploadingImage.value = true
  error.value = null
  try {
    const url = await store.upload(file)
    form.value.image_url = url
  } catch (err) {
    error.value = err.message
  } finally {
    uploadingImage.value = false
  }
}

function removeImage() {
  form.value.image_url = null
}

async function handleSubmit() {
  saving.value = true
  error.value = null
  try {
    const topic = await store.addTopic(form.value)

    if (generateAfterSave.value) {
      await store.generateContent(topic.id, generatePlatform.value, generateType.value)
    }

    router.push('/research')
  } catch (err) {
    error.value = err.message
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="mx-auto max-w-2xl px-4 py-8 sm:px-6 lg:px-8">
    <h1 class="text-2xl font-bold text-go4-secondary">Eigenes Thema erstellen</h1>
    <p class="mt-1 text-go4-muted">Beschreibe ein Thema und generiere sofort Content daraus.</p>

    <div v-if="error" class="mt-4 rounded-lg bg-red-50 p-4 text-sm text-red-700">
      {{ error }}
    </div>

    <form class="mt-6 space-y-6" @submit.prevent="handleSubmit">
      <!-- Title -->
      <div>
        <label class="block text-sm font-medium text-go4-secondary">Titel</label>
        <input
          v-model="form.title"
          type="text"
          required
          class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
          placeholder="z.B. Solar-Carport Vorteile"
        />
      </div>

      <!-- Description -->
      <div>
        <label class="block text-sm font-medium text-go4-secondary">Beschreibung</label>
        <textarea
          v-model="form.description"
          rows="4"
          required
          class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
          placeholder="Warum ist dieses Thema relevant? Welche Aspekte sollen beleuchtet werden?"
        />
      </div>

      <!-- Category -->
      <div>
        <label class="block text-sm font-medium text-go4-secondary">Kategorie</label>
        <select
          v-model="form.category"
          class="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
        >
          <option value="content">Content</option>
          <option value="social">Social Media</option>
          <option value="email">E-Mail</option>
          <option value="general">Allgemein</option>
        </select>
      </div>

      <!-- Platforms -->
      <div>
        <label class="block text-sm font-medium text-go4-secondary">Plattformen</label>
        <div class="mt-2 flex flex-wrap gap-3">
          <label
            v-for="opt in platformOptions"
            :key="opt.value"
            class="inline-flex cursor-pointer items-center gap-2 rounded-lg border px-4 py-2 text-sm transition"
            :class="
              form.platforms.includes(opt.value)
                ? 'border-go4-primary bg-go4-primary/5 text-go4-primary'
                : 'border-gray-300 text-go4-muted hover:border-gray-400'
            "
          >
            <input
              type="checkbox"
              class="hidden"
              :checked="form.platforms.includes(opt.value)"
              @change="togglePlatform(opt.value)"
            />
            {{ opt.label }}
          </label>
        </div>
      </div>

      <!-- Priority -->
      <div>
        <label class="block text-sm font-medium text-go4-secondary">
          Priorität: {{ form.priority }}
          <span class="font-normal text-go4-muted">
            ({{ ['', 'Sehr hoch', 'Hoch', 'Normal', 'Niedrig', 'Sehr niedrig'][form.priority] }})
          </span>
        </label>
        <input v-model.number="form.priority" type="range" min="1" max="5" class="mt-2 w-full" />
      </div>

      <!-- Image Upload -->
      <div>
        <label class="block text-sm font-medium text-go4-secondary">Bild (optional)</label>
        <div v-if="form.image_url" class="mt-2">
          <img :src="form.image_url" alt="Vorschau" class="h-32 rounded-lg object-cover" />
          <button
            type="button"
            class="mt-2 text-sm text-red-600 hover:text-red-800"
            @click="removeImage"
          >
            Bild entfernen
          </button>
        </div>
        <div v-else class="mt-2">
          <label
            class="flex cursor-pointer items-center justify-center rounded-lg border-2 border-dashed border-gray-300 p-6 text-sm text-go4-muted transition hover:border-go4-primary hover:text-go4-primary"
          >
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              class="hidden"
              :disabled="uploadingImage"
              @change="handleImageUpload"
            />
            {{ uploadingImage ? 'Hochladen...' : 'Bild auswählen oder hierher ziehen' }}
          </label>
        </div>
      </div>

      <!-- Generate Options -->
      <div class="rounded-lg border border-gray-200 bg-gray-50 p-4">
        <label class="flex items-center gap-2">
          <input v-model="generateAfterSave" type="checkbox" class="rounded" />
          <span class="text-sm font-medium text-go4-secondary"> Sofort Content generieren </span>
        </label>
        <div v-if="generateAfterSave" class="mt-3 flex gap-4">
          <div class="flex-1">
            <label class="block text-xs font-medium text-go4-muted">Plattform</label>
            <select
              v-model="generatePlatform"
              class="mt-1 block w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
            >
              <option value="facebook">Facebook</option>
              <option value="instagram">Instagram</option>
              <option value="linkedin">LinkedIn</option>
              <option value="email">E-Mail</option>
            </select>
          </div>
          <div class="flex-1">
            <label class="block text-xs font-medium text-go4-muted">Content-Typ</label>
            <select
              v-model="generateType"
              class="mt-1 block w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
            >
              <option value="post">Post</option>
              <option value="story">Story</option>
              <option value="reel">Reel</option>
              <option value="email">E-Mail</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="flex gap-3">
        <button
          type="submit"
          :disabled="saving"
          class="rounded-lg bg-go4-primary px-6 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90 disabled:opacity-50"
        >
          {{ saving ? 'Speichern...' : generateAfterSave ? 'Speichern & generieren' : 'Speichern' }}
        </button>
        <router-link
          to="/research"
          class="rounded-lg border border-gray-300 px-6 py-2 text-sm font-medium text-go4-secondary hover:bg-gray-50"
        >
          Abbrechen
        </router-link>
      </div>
    </form>
  </div>
</template>
