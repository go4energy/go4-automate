<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useModuleStore } from '@/stores/modules'
import { useAuthStore } from '@/stores/auth'

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

const categoryLabels = {
  marketing: 'Marketing',
  system: 'System & Tools'
}

// Filter desktop modules by user permissions
const filteredDesktopGrouped = computed(() => {
  const result = {}
  for (const [category, mods] of Object.entries(moduleStore.desktopGrouped)) {
    const filtered = mods.filter(
      (mod) => !mod.name || authStore.isAdmin || authStore.canViewModule(mod.name)
    )
    if (filtered.length > 0) result[category] = filtered
  }
  return result
})

function navigateTo(mod) {
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
    <svg class="absolute" style="width: 0; height: 0">
      <defs>
        <filter id="desktopBlur">
          <feGaussianBlur in="SourceGraphic" stdDeviation="40" result="blur" />
        </filter>
      </defs>
    </svg>

    <!-- Animated gradient blobs — opacity 20% -->
    <div class="absolute inset-0 opacity-20" style="filter: url(#desktopBlur)">
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
      <div class="flex w-full max-w-3xl flex-1 flex-col items-center justify-center px-6 pb-[33vh]">
        <div v-if="moduleStore.loading" class="flex items-center justify-center py-12">
          <span class="text-sm text-gray-400 dark:text-gray-500">Module laden...</span>
        </div>
        <div
          v-else-if="moduleStore.error"
          class="rounded-lg bg-red-500/10 p-4 text-center text-sm text-red-600 backdrop-blur dark:bg-red-900/20 dark:text-red-400"
        >
          {{ moduleStore.error }}
        </div>
        <div v-else class="w-full space-y-10">
          <div v-for="(mods, category) in filteredDesktopGrouped" :key="category">
            <p
              class="mb-5 text-center text-[10px] font-semibold uppercase tracking-[0.2em] text-gray-600 dark:text-gray-400/60"
            >
              {{ categoryLabels[category] || category }}
            </p>
            <div
              class="grid grid-cols-3 justify-items-center gap-x-10 gap-y-8 sm:grid-cols-4 lg:grid-cols-6"
            >
              <button
                v-for="mod in mods"
                :key="mod.name"
                class="group flex w-20 flex-col items-center gap-2.5"
                @click="navigateTo(mod)"
              >
                <div class="relative">
                  <div
                    class="relative flex h-[68px] w-[68px] items-center justify-center rounded-[18px] transition-all duration-300 group-hover:scale-110"
                  >
                    <div
                      class="absolute inset-0 rounded-[18px] opacity-[0.15] shadow-lg transition-all duration-300 group-hover:opacity-100 group-hover:shadow-xl"
                      :style="{
                        background: `linear-gradient(135deg, ${mod.color}, ${mod.color}CC)`,
                        boxShadow: `0 4px 14px ${mod.color}30`
                      }"
                    />
                    <svg
                      class="relative h-7 w-7 text-go4-secondary drop-shadow dark:text-white"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="1.5"
                    >
                      <path stroke-linecap="round" stroke-linejoin="round" :d="mod.icon" />
                    </svg>
                  </div>
                  <span
                    v-if="mod.badge_count > 0"
                    class="absolute -right-1 -top-1 flex h-5 min-w-5 animate-pulse items-center justify-center rounded-full bg-red-500 px-1 text-xs font-bold text-white"
                  >
                    {{ mod.badge_count > 99 ? '99+' : mod.badge_count }}
                  </span>
                </div>
                <span
                  class="text-center text-[11px] font-medium text-go4-secondary transition-colors dark:text-white"
                >
                  {{ mod.label }}
                </span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
