<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useModuleStore } from '@/stores/modules'
import { useAuthStore } from '@/stores/auth'
import { bulkUpdateDesktopOrder } from '@/api/settings'

const router = useRouter()
const moduleStore = useModuleStore()
const authStore = useAuthStore()

// Interactive gradient blob follows cursor
const interactiveRef = ref(null)
let curX = 0
let curY = 0
let tgX = 0
let tgY = 0
let animationId = null

function onMouseMove(e) {
  tgX = e.clientX
  tgY = e.clientY
}

function moveInteractive() {
  curX += (tgX - curX) / 20
  curY += (tgY - curY) / 20
  if (interactiveRef.value) {
    interactiveRef.value.style.transform = `translate(${Math.round(curX)}px, ${Math.round(curY)}px)`
  }
  animationId = requestAnimationFrame(moveInteractive)
}

// Edit mode for drag-and-drop
const editMode = ref(false)
const dragIndex = ref(null)
const dropIndex = ref(null)
const localOrder = ref([])
const saving = ref(false)

// Flat filtered list — no categories
const filteredModules = computed(() => {
  return moduleStore.desktopSorted.filter(
    (mod) => !mod.name || authStore.isAdmin || authStore.canViewModule(mod.name)
  )
})

// In edit mode, use local reorderable list
const displayModules = computed(() => {
  if (editMode.value && localOrder.value.length) return localOrder.value
  return filteredModules.value
})

function enterEditMode() {
  localOrder.value = [...filteredModules.value]
  editMode.value = true
}

function cancelEditMode() {
  editMode.value = false
  localOrder.value = []
  dragIndex.value = null
  dropIndex.value = null
}

async function saveOrder() {
  saving.value = true
  try {
    const orderMap = {}
    localOrder.value.forEach((mod, idx) => {
      orderMap[mod.name] = idx + 1
    })
    await bulkUpdateDesktopOrder(orderMap)
    await moduleStore.fetchDesktop()
    editMode.value = false
    localOrder.value = []
  } catch (err) {
    console.error('Failed to save order:', err)
  } finally {
    saving.value = false
  }
}

// HTML5 Drag-and-Drop handlers
function onDragStart(e, index) {
  dragIndex.value = index
  e.dataTransfer.effectAllowed = 'move'
  e.dataTransfer.setData('text/plain', index)
  e.target.closest('[data-tile]').classList.add('opacity-40')
}

function onDragEnd(e) {
  e.target.closest('[data-tile]')?.classList.remove('opacity-40')
  dragIndex.value = null
  dropIndex.value = null
}

function onDragOver(e, index) {
  e.preventDefault()
  e.dataTransfer.dropEffect = 'move'
  dropIndex.value = index
}

function onDragLeave() {
  dropIndex.value = null
}

function onDrop(e, index) {
  e.preventDefault()
  const from = dragIndex.value
  if (from === null || from === index) return
  const item = localOrder.value.splice(from, 1)[0]
  localOrder.value.splice(index, 0, item)
  dragIndex.value = null
  dropIndex.value = null
}

function navigateTo(mod) {
  if (editMode.value) return
  if (mod.external_url) {
    window.open(mod.external_url, '_blank')
    return
  }
  const route = mod.frontend?.base_route || `/${mod.name}`
  router.push(route)
}

onMounted(() => {
  moduleStore.fetchDesktop()
  window.addEventListener('mousemove', onMouseMove)
  moveInteractive()
})

onUnmounted(() => {
  window.removeEventListener('mousemove', onMouseMove)
  if (animationId) cancelAnimationFrame(animationId)
})
</script>

<template>
  <div class="-m-6 relative min-h-[calc(100vh-3.5rem)] overflow-hidden">
    <!-- Base background -->
    <div
      class="absolute inset-0 bg-gradient-to-br from-[#E8EDFF] via-[#DED8FF] to-[#FFE8D8] dark:from-[#0A0015] dark:via-[#000A1A] dark:to-[#050510]"
    />

    <!-- SVG blur filter -->
    <svg
      class="absolute"
      style="width: 0; height: 0"
    >
      <defs>
        <filter id="desktopBlur">
          <feGaussianBlur
            in="SourceGraphic"
            stdDeviation="40"
            result="blur"
          />
        </filter>
      </defs>
    </svg>

    <!-- Animated gradient blobs — opacity 20% -->
    <div
      class="absolute inset-0 opacity-20"
      style="filter: url(#desktopBlur)"
    >
      <!-- First: Blue — moves vertically, top-center -->
      <div
        class="absolute left-[5%] top-0 h-[80%] w-[80%] animate-first rounded-full mix-blend-hard-light"
        style="
          background: radial-gradient(
            circle at center,
            rgba(18, 113, 255, 0.8) 0,
            rgba(18, 113, 255, 0) 50%
          );
        "
      />
      <!-- Second: Purple — orbits reverse, offset top-right -->
      <div
        class="absolute left-[25%] top-[-10%] h-[80%] w-[80%] animate-second rounded-full mix-blend-hard-light"
        style="
          background: radial-gradient(
            circle at center,
            rgba(140, 60, 255, 0.8) 0,
            rgba(140, 60, 255, 0) 50%
          );
        "
      />
      <!-- Third: Cyan — drifts slowly, offset left -->
      <div
        class="absolute left-[-10%] top-[20%] h-[80%] w-[80%] animate-third rounded-full mix-blend-hard-light"
        style="
          background: radial-gradient(
            circle at center,
            rgba(100, 200, 255, 0.8) 0,
            rgba(100, 200, 255, 0) 50%
          );
        "
      />
      <!-- Fourth: go4 Orange — moves horizontally, center -->
      <div
        class="absolute left-[15%] top-[10%] h-[80%] w-[80%] animate-fourth rounded-full mix-blend-hard-light"
        style="
          background: radial-gradient(
            circle at center,
            rgba(255, 102, 0, 0.8) 0,
            rgba(255, 102, 0, 0) 50%
          );
        "
      />
      <!-- Fifth: Rose — orbits, offset bottom-right -->
      <div
        class="absolute left-[20%] top-[15%] h-[80%] w-[80%] animate-fifth rounded-full mix-blend-hard-light"
        style="
          background: radial-gradient(
            circle at center,
            rgba(255, 60, 130, 0.8) 0,
            rgba(255, 60, 130, 0) 50%
          );
        "
      />
      <!-- Interactive: follows cursor -->
      <div
        ref="interactiveRef"
        class="absolute -left-1/2 -top-1/2 h-full w-full rounded-full opacity-70 mix-blend-hard-light"
        style="
          background: radial-gradient(
            circle at center,
            rgba(255, 130, 50, 0.8) 0,
            rgba(255, 130, 50, 0) 50%
          );
        "
      />
    </div>

    <!-- Content overlay -->
    <div class="relative flex min-h-[calc(100vh-3.5rem)] flex-col items-center">
      <!-- Edit mode toolbar -->
      <div
        v-if="authStore.isAdmin"
        class="absolute right-4 top-4 z-10 flex items-center gap-2"
      >
        <template v-if="editMode">
          <button
            class="rounded-lg bg-white/80 px-3 py-1.5 text-sm font-medium text-gray-600 backdrop-blur transition hover:bg-white dark:bg-white/10 dark:text-gray-300 dark:hover:bg-white/20"
            :disabled="saving"
            @click="cancelEditMode"
          >
            Abbrechen
          </button>
          <button
            class="rounded-lg bg-go4-primary px-3 py-1.5 text-sm font-medium text-white transition hover:bg-go4-primary/90 disabled:opacity-50"
            :disabled="saving"
            @click="saveOrder"
          >
            {{ saving ? 'Speichern...' : 'Speichern' }}
          </button>
        </template>
        <button
          v-else
          class="rounded-lg bg-white/60 p-2 text-gray-500 backdrop-blur transition hover:bg-white/80 hover:text-gray-700 dark:bg-white/10 dark:text-gray-400 dark:hover:bg-white/20 dark:hover:text-white"
          title="Reihenfolge ändern"
          @click="enterEditMode"
        >
          <svg
            class="h-5 w-5"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"
            />
          </svg>
        </button>
      </div>

      <div class="flex w-full max-w-3xl flex-1 flex-col items-center justify-center px-6 pb-[33vh]">
        <div
          v-if="moduleStore.loading"
          class="flex items-center justify-center py-12"
        >
          <span class="text-sm text-gray-400 dark:text-gray-500">Module laden...</span>
        </div>
        <div
          v-else-if="moduleStore.error"
          class="rounded-lg bg-red-500/10 p-4 text-center text-sm text-red-600 backdrop-blur dark:bg-red-900/20 dark:text-red-400"
        >
          {{ moduleStore.error }}
        </div>
        <div
          v-else
          class="w-full"
        >
          <!-- Edit mode hint -->
          <p
            v-if="editMode"
            class="mb-6 text-center text-sm text-gray-500 dark:text-gray-400"
          >
            Kacheln per Drag & Drop verschieben
          </p>
          <div
            class="grid grid-cols-2 justify-items-center gap-x-14 gap-y-12 sm:grid-cols-3 lg:grid-cols-5"
          >
            <div
              v-for="(mod, index) in displayModules"
              :key="mod.name"
              data-tile
              class="flex w-[120px] flex-col items-center gap-4 transition-transform"
              :class="[
                editMode ? 'cursor-grab active:cursor-grabbing' : 'cursor-pointer',
                dropIndex === index && dragIndex !== index ? 'scale-105' : '',
              ]"
              :draggable="editMode"
              @dragstart="editMode && onDragStart($event, index)"
              @dragend="onDragEnd"
              @dragover="editMode && onDragOver($event, index)"
              @dragleave="onDragLeave"
              @drop="editMode && onDrop($event, index)"
              @click="navigateTo(mod)"
            >
              <div class="relative">
                <div
                  class="relative flex h-[102px] w-[102px] items-center justify-center rounded-[27px] transition-all duration-300"
                  :class="editMode ? 'group-hover:scale-100' : 'group hover:scale-110'"
                >
                  <div
                    class="absolute inset-0 rounded-[27px] shadow-lg transition-all duration-300"
                    :class="editMode ? 'opacity-30' : 'opacity-[0.15] group-hover:opacity-100 group-hover:shadow-xl'"
                    :style="{
                      background: `linear-gradient(135deg, ${mod.color}, ${mod.color}CC)`,
                      boxShadow: `0 6px 20px ${mod.color}30`
                    }"
                  />
                  <svg
                    class="relative h-11 w-11 text-go4-secondary drop-shadow dark:text-white"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="1.125"
                    overflow="visible"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      :d="mod.icon"
                    />
                  </svg>
                </div>
                <span
                  v-if="mod.badge_count > 0 && !editMode"
                  class="absolute -right-1 -top-1 flex h-6 min-w-6 animate-pulse items-center justify-center rounded-full bg-red-500 px-1.5 text-sm font-bold text-white"
                >
                  {{ mod.badge_count > 99 ? '99+' : mod.badge_count }}
                </span>
                <!-- Drag handle indicator in edit mode -->
                <div
                  v-if="editMode"
                  class="absolute -right-1 -top-1 flex h-6 w-6 items-center justify-center rounded-full bg-white/80 text-gray-400 shadow dark:bg-gray-700 dark:text-gray-300"
                >
                  <svg
                    class="h-3.5 w-3.5"
                    viewBox="0 0 24 24"
                    fill="currentColor"
                  >
                    <circle
                      cx="9"
                      cy="5"
                      r="1.5"
                    />
                    <circle
                      cx="15"
                      cy="5"
                      r="1.5"
                    />
                    <circle
                      cx="9"
                      cy="12"
                      r="1.5"
                    />
                    <circle
                      cx="15"
                      cy="12"
                      r="1.5"
                    />
                    <circle
                      cx="9"
                      cy="19"
                      r="1.5"
                    />
                    <circle
                      cx="15"
                      cy="19"
                      r="1.5"
                    />
                  </svg>
                </div>
              </div>
              <span
                class="text-center text-base font-medium text-go4-secondary transition-colors dark:text-white"
              >
                {{ mod.label }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
