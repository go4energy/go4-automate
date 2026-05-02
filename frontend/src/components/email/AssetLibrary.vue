<script setup>
/**
 * Drag-Drop image / file upload + tenant-scoped asset library.
 *
 * Click on a thumbnail = copy URL to clipboard (for inserting into HTML).
 * Trash icon = delete (server + DB row).
 */
import { ref, onMounted, computed } from 'vue'
import api from '@/api'

const props = defineProps({
  // emit on click instead of just copying — for embedding in editor
  selectable: { type: Boolean, default: false },
})
const emit = defineEmits(['select'])

const assets = ref([])
const loading = ref(false)
const uploading = ref(false)
const error = ref(null)
const dragging = ref(false)
const fileInput = ref(null)

const apiBase = '/v1/emailmarketing/assets'

async function load() {
  loading.value = true
  error.value = null
  try {
    const { data } = await api.get(apiBase)
    assets.value = data
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    loading.value = false
  }
}

async function uploadFiles(fileList) {
  if (!fileList || fileList.length === 0) return
  uploading.value = true
  error.value = null
  try {
    for (const file of fileList) {
      const fd = new FormData()
      fd.append('file', file)
      try {
        const { data } = await api.post(apiBase, fd, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
        assets.value.unshift(data)
      } catch (e) {
        error.value = `${file.name}: ${e.response?.data?.detail || e.message}`
      }
    }
  } finally {
    uploading.value = false
  }
}

function onFileChange(e) {
  uploadFiles(e.target.files)
  e.target.value = '' // reset so same file can be re-selected
}

function onDrop(e) {
  e.preventDefault()
  dragging.value = false
  uploadFiles(e.dataTransfer.files)
}

async function deleteAsset(asset) {
  if (!confirm(`"${asset.original_filename}" wirklich löschen?`)) return
  try {
    await api.delete(`${apiBase}/${asset.id}`)
    assets.value = assets.value.filter((a) => a.id !== asset.id)
  } catch (e) {
    alert(e.response?.data?.detail || e.message)
  }
}

function clickAsset(asset) {
  if (props.selectable) {
    emit('select', asset)
  } else {
    copyUrl(asset)
  }
}

async function copyUrl(asset) {
  try {
    await navigator.clipboard.writeText(asset.url_path)
    // Tiny visual feedback: temporarily mark this asset
    asset._justCopied = Date.now()
    setTimeout(() => {
      asset._justCopied = 0
    }, 1500)
  } catch {
    // ignore
  }
}

function isImage(mime) {
  return mime.startsWith('image/')
}

function fmtSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

const empty = computed(() => !loading.value && assets.value.length === 0)

onMounted(load)

defineExpose({ load })
</script>

<template>
  <div>
    <!-- Drop-Zone -->
    <div
      class="rounded-lg border-2 border-dashed p-6 text-center transition-colors"
      :class="dragging
        ? 'border-go4-primary bg-go4-primary/5'
        : 'border-gray-300 dark:border-gray-600'"
      @dragover.prevent="dragging = true"
      @dragleave.prevent="dragging = false"
      @drop="onDrop"
      @click="fileInput.click()"
      style="cursor: pointer;"
    >
      <svg
        class="mx-auto h-10 w-10 text-gray-400"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="1.5"
          d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
        />
      </svg>
      <p class="mt-2 text-sm text-gray-700 dark:text-gray-300">
        <strong>Klicken</strong> oder Dateien hier rein <strong>ziehen</strong>
      </p>
      <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
        Bilder (JPG/PNG/GIF/WebP/SVG) oder PDF, max. 5 MB pro Datei
      </p>
      <input
        ref="fileInput"
        type="file"
        multiple
        accept="image/*,application/pdf"
        class="hidden"
        @change="onFileChange"
      >
    </div>

    <div
      v-if="uploading"
      class="mt-3 text-xs text-gray-500"
    >
      Lade hoch…
    </div>
    <div
      v-if="error"
      class="mt-3 rounded bg-red-50 dark:bg-red-900/20 p-2 text-xs text-red-700 dark:text-red-300"
    >
      {{ error }}
    </div>

    <!-- Library Grid -->
    <div class="mt-6">
      <div
        v-if="loading"
        class="text-sm text-gray-500"
      >
        Laden…
      </div>
      <div
        v-else-if="empty"
        class="text-center text-sm text-gray-500 dark:text-gray-400 py-6"
      >
        Noch keine Bilder oder Dateien hochgeladen.
      </div>
      <div
        v-else
        class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3"
      >
        <div
          v-for="asset in assets"
          :key="asset.id"
          class="group relative rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 overflow-hidden cursor-pointer hover:border-go4-primary"
          @click="clickAsset(asset)"
        >
          <!-- Thumbnail -->
          <div class="aspect-square flex items-center justify-center bg-gray-50 dark:bg-gray-800">
            <img
              v-if="isImage(asset.mime_type)"
              :src="asset.url_path"
              :alt="asset.original_filename"
              class="max-h-full max-w-full object-contain"
            >
            <div
              v-else
              class="flex flex-col items-center text-gray-400"
            >
              <svg
                class="h-12 w-12"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="1.5"
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              <span class="text-xs mt-1">PDF</span>
            </div>
          </div>

          <!-- Footer -->
          <div class="p-2 text-xs">
            <p
              class="truncate text-gray-700 dark:text-gray-300"
              :title="asset.original_filename"
            >
              {{ asset.original_filename }}
            </p>
            <p class="text-gray-400">
              {{ fmtSize(asset.size_bytes) }}
            </p>
          </div>

          <!-- Just-copied indicator -->
          <div
            v-if="asset._justCopied"
            class="absolute inset-0 bg-emerald-500/90 flex items-center justify-center text-white text-xs font-medium"
          >
            ✓ URL kopiert
          </div>

          <!-- Actions -->
          <button
            type="button"
            class="absolute top-1 right-1 rounded-full bg-white/90 hover:bg-red-50 p-1 opacity-0 group-hover:opacity-100 transition-opacity"
            title="Löschen"
            @click.stop="deleteAsset(asset)"
          >
            <svg
              class="h-4 w-4 text-red-600"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
