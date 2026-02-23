<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useCollectorStore } from '@/stores/collector'
import PageHeader from '@/components/ui/PageHeader.vue'
import TagSelector from '@/components/ui/TagSelector.vue'
import StreamSelector from '@/components/ui/StreamSelector.vue'

const router = useRouter()
const store = useCollectorStore()

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
  image_url: null,
  tags: [],
  streams: [],
  group_id: store.activeGroupId
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

    router.push('/collector')
  } catch (err) {
    error.value = err.message
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="mx-auto max-w-2xl">
    <PageHeader
      title="Eigenes Thema erstellen"
      subtitle="Beschreibe ein Thema und generiere sofort Content daraus."
    />

    <div
      v-if="error"
      class="mt-4 rounded-lg bg-red-50 dark:bg-red-900/20 p-4 text-sm text-red-700 dark:text-red-400"
    >
      {{ error }}
    </div>

    <form class="mt-6 space-y-6" @submit.prevent="handleSubmit">
      <div>
        <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">Titel</label>
        <input
          v-model="form.title"
          type="text"
          required
          class="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm dark:bg-gray-700 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
          placeholder="z.B. Solar-Carport Vorteile"
        />
      </div>

      <div>
        <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100"
          >Beschreibung</label
        >
        <textarea
          v-model="form.description"
          rows="4"
          required
          class="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm dark:bg-gray-700 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
          placeholder="Warum ist dieses Thema relevant? Welche Aspekte sollen beleuchtet werden?"
        />
      </div>

      <div>
        <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100"
          >Kategorie</label
        >
        <select
          v-model="form.category"
          class="mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm dark:bg-gray-700 dark:text-gray-100 focus:border-go4-primary focus:outline-none focus:ring-1 focus:ring-go4-primary"
        >
          <option value="content">Content</option>
          <option value="social">Social Media</option>
          <option value="email">E-Mail</option>
          <option value="general">Allgemein</option>
        </select>
      </div>

      <div>
        <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100"
          >Plattformen</label
        >
        <div class="mt-2 flex flex-wrap gap-3">
          <label
            v-for="opt in platformOptions"
            :key="opt.value"
            class="inline-flex cursor-pointer items-center gap-2 rounded-lg border px-4 py-2 text-sm transition"
            :class="
              form.platforms.includes(opt.value)
                ? 'border-go4-primary bg-go4-primary/5 text-go4-primary'
                : 'border-gray-300 dark:border-gray-600 text-go4-muted dark:text-gray-400 hover:border-gray-400'
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

      <div>
        <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100">
          Prioritaet: {{ form.priority }}
          <span class="font-normal text-go4-muted dark:text-gray-400">
            ({{ ['', 'Sehr hoch', 'Hoch', 'Normal', 'Niedrig', 'Sehr niedrig'][form.priority] }})
          </span>
        </label>
        <input v-model.number="form.priority" type="range" min="1" max="5" class="mt-2 w-full" />
      </div>

      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div>
          <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100"
            >Tags</label
          >
          <div class="mt-1">
            <TagSelector v-model="form.tags" placeholder="Tags auswaehlen..." />
          </div>
        </div>
        <div>
          <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100"
            >Streams</label
          >
          <div class="mt-1">
            <StreamSelector v-model="form.streams" placeholder="Streams auswaehlen..." />
          </div>
        </div>
      </div>

      <div>
        <label class="block text-sm font-medium text-go4-secondary dark:text-gray-100"
          >Bild (optional)</label
        >
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
            class="flex cursor-pointer items-center justify-center rounded-lg border-2 border-dashed border-gray-300 dark:border-gray-600 p-6 text-sm text-go4-muted dark:text-gray-400 transition hover:border-go4-primary hover:text-go4-primary"
          >
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              class="hidden"
              :disabled="uploadingImage"
              @change="handleImageUpload"
            />
            {{ uploadingImage ? 'Hochladen...' : 'Bild auswaehlen oder hierher ziehen' }}
          </label>
        </div>
      </div>

      <div
        class="rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 p-4"
      >
        <label class="flex items-center gap-2">
          <input v-model="generateAfterSave" type="checkbox" class="rounded" />
          <span class="text-sm font-medium text-go4-secondary dark:text-gray-100">
            Sofort Content generieren
          </span>
        </label>
        <div v-if="generateAfterSave" class="mt-3 flex gap-4">
          <div class="flex-1">
            <label class="block text-xs font-medium text-go4-muted dark:text-gray-400"
              >Plattform</label
            >
            <select
              v-model="generatePlatform"
              class="mt-1 block w-full rounded border border-gray-300 dark:border-gray-600 px-2 py-1.5 text-sm dark:bg-gray-700 dark:text-gray-100"
            >
              <option value="facebook">Facebook</option>
              <option value="instagram">Instagram</option>
              <option value="linkedin">LinkedIn</option>
              <option value="email">E-Mail</option>
            </select>
          </div>
          <div class="flex-1">
            <label class="block text-xs font-medium text-go4-muted dark:text-gray-400"
              >Content-Typ</label
            >
            <select
              v-model="generateType"
              class="mt-1 block w-full rounded border border-gray-300 dark:border-gray-600 px-2 py-1.5 text-sm dark:bg-gray-700 dark:text-gray-100"
            >
              <option value="post">Post</option>
              <option value="story">Story</option>
              <option value="reel">Reel</option>
              <option value="email">E-Mail</option>
            </select>
          </div>
        </div>
      </div>

      <div class="flex gap-3">
        <button
          type="submit"
          :disabled="saving"
          class="rounded-lg bg-go4-primary px-6 py-2 text-sm font-medium text-white transition hover:bg-go4-primary/90 disabled:opacity-50"
        >
          {{ saving ? 'Speichern...' : generateAfterSave ? 'Speichern & generieren' : 'Speichern' }}
        </button>
        <router-link
          to="/collector"
          class="rounded-lg border border-gray-300 dark:border-gray-600 px-6 py-2 text-sm font-medium text-go4-secondary dark:text-gray-100 hover:bg-gray-50 dark:hover:bg-gray-700"
        >
          Abbrechen
        </router-link>
      </div>
    </form>
  </div>
</template>
