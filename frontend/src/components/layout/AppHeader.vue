<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLayoutStore } from '@/stores/layout'
import { useAuthStore } from '@/stores/auth'
import { usePipelineContext } from '@/stores/pipelineContext'
import { useEngagementStore } from '@/stores/engagement'
import PasswordChangeModal from '@/components/auth/PasswordChangeModal.vue'

const route = useRoute()
const router = useRouter()
const layout = useLayoutStore()
const authStore = useAuthStore()
const pipelineCtx = usePipelineContext()
const engagementStore = useEngagementStore()

const userMenuOpen = ref(false)
const showPasswordModal = ref(false)
const pipelineMenuOpen = ref(false)

// Pipeline selector only visible on pipeline-relevant modules
const pipelineModulePrefixes = ['/engagement', '/linkedin', '/contacts', '/crm', '/letter', '/campaigns', '/whatsapp', '/emailmarketing']
const showPipelineSelector = computed(() => {
  const path = route.path
  return pipelineModulePrefixes.some((prefix) => path.startsWith(prefix))
})

const sortedPipelines = computed(() => {
  const all = engagementStore.activePipelines
  if (!pipelineCtx.activePipelineId) return all
  const active = all.filter((p) => p.id === pipelineCtx.activePipelineId)
  const rest = all.filter((p) => p.id !== pipelineCtx.activePipelineId)
  return [...active, ...rest]
})

onMounted(() => {
  pipelineCtx.ensurePipelines()
})

const breadcrumbs = computed(() => {
  const crumbs = []
  const name = route.name

  if (name === 'desktop') return crumbs

  // Build full parent chain from breadcrumb.parent
  const buildParentChain = (routeName) => {
    const matchedRoute = router.getRoutes().find((r) => r.name === routeName)
    if (!matchedRoute) return

    const meta = matchedRoute.meta || {}
    const breadcrumb = meta.breadcrumb || {}

    // First, recursively add parents
    if (breadcrumb.parent) {
      buildParentChain(breadcrumb.parent)
    }

    // Then add this route
    crumbs.push({
      label: breadcrumb.label || meta.title || routeName,
      to: matchedRoute.path.includes(':') ? null : { name: routeName }
    })
  }

  // Check for new breadcrumb.parent format first
  if (route.meta?.breadcrumb?.parent) {
    buildParentChain(route.meta.breadcrumb.parent)
  }
  // Fallback to old parent format
  else if (route.meta?.parent) {
    const parentRoute = router.getRoutes().find((r) => r.name === route.meta.parent)
    if (parentRoute) {
      crumbs.push({
        label: parentRoute.meta?.breadcrumb?.label || parentRoute.meta?.title || parentRoute.name,
        to: { name: parentRoute.name }
      })
    }
  }

  // Current page (always last, not clickable)
  const currentLabel = route.meta?.breadcrumb?.label || route.meta?.title || name
  crumbs.push({
    label: currentLabel,
    to: null
  })

  return crumbs
})

function handleLogout() {
  userMenuOpen.value = false
  authStore.logout()
  router.push('/login')
}

function openPasswordModal() {
  showPasswordModal.value = true
  userMenuOpen.value = false
}

function closeMenuOnOutsideClick() {
  userMenuOpen.value = false
}
</script>

<template>
  <header
    class="sticky top-0 z-20 flex h-14 items-center justify-between border-b border-gray-200/60 bg-white/80 px-6 backdrop-blur-md transition-colors dark:border-gray-700/60 dark:bg-go4-dark-bg/80"
  >
    <!-- Breadcrumbs -->
    <nav class="flex items-center gap-1.5 text-sm">
      <template v-if="breadcrumbs.length > 0">
        <!-- Home icon as first crumb -->
        <router-link
          to="/"
          class="text-gray-600 transition hover:text-go4-primary dark:text-gray-300 dark:hover:text-go4-primary"
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
              d="M2.25 12l8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25"
            />
          </svg>
        </router-link>
        <template
          v-for="(crumb, i) in breadcrumbs"
          :key="i"
        >
          <span class="text-gray-300 dark:text-gray-600">/</span>
          <router-link
            v-if="crumb.to && i < breadcrumbs.length - 1"
            :to="crumb.to"
            class="text-gray-500 transition hover:text-go4-secondary dark:text-gray-400 dark:hover:text-gray-200"
          >
            {{ crumb.label }}
          </router-link>
          <span
            v-else
            class="font-medium text-go4-secondary dark:text-gray-100"
          >
            {{ crumb.label }}
          </span>
        </template>
      </template>
    </nav>

    <!-- Center: Pipeline Context Selector (only on pipeline-relevant modules) -->
    <div
      v-if="showPipelineSelector"
      class="relative"
    >
      <button
        class="flex items-center gap-2 rounded-lg border px-3 py-1.5 text-sm transition"
        :class="
          pipelineCtx.isActive
            ? 'border-go4-primary/30 bg-go4-primary/5 text-go4-primary dark:border-go4-primary/40 dark:bg-go4-primary/10'
            : 'border-gray-200 text-gray-500 hover:border-gray-300 hover:text-gray-700 dark:border-gray-600 dark:text-gray-400 dark:hover:border-gray-500'
        "
        @click="pipelineMenuOpen = !pipelineMenuOpen"
      >
        <svg
          class="h-4 w-4"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z"
          />
        </svg>
        <span class="max-w-[200px] truncate">{{ pipelineCtx.label }}</span>
        <svg
          class="h-3.5 w-3.5 shrink-0"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M19.5 8.25l-7.5 7.5-7.5-7.5"
          />
        </svg>
      </button>

      <!-- Pipeline Dropdown -->
      <div
        v-if="pipelineMenuOpen"
        class="absolute left-0 top-full z-50 mt-1 w-72 rounded-lg border border-gray-200 bg-white py-1 shadow-lg dark:border-gray-700 dark:bg-gray-800"
      >
        <button
          class="flex w-full items-center gap-2 px-4 py-2 text-sm transition"
          :class="
            !pipelineCtx.isActive
              ? 'bg-go4-primary/5 font-medium text-go4-primary'
              : 'text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700'
          "
          @click="pipelineCtx.clearPipeline(); pipelineMenuOpen = false"
        >
          <svg
            class="h-4 w-4"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z"
            />
          </svg>
          Alle Pipelines
        </button>
        <div class="my-1 border-t border-gray-100 dark:border-gray-700" />
        <button
          v-for="pipeline in sortedPipelines"
          :key="pipeline.id"
          class="flex w-full items-center gap-2 px-4 py-2 text-sm transition"
          :class="
            pipelineCtx.activePipelineId === pipeline.id
              ? 'bg-go4-primary/5 font-medium text-go4-primary'
              : 'text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700'
          "
          @click="pipelineCtx.setActivePipeline(pipeline.id); pipelineMenuOpen = false"
        >
          <span
            class="h-2 w-2 shrink-0 rounded-full"
            :class="pipeline.is_active ? 'bg-green-400' : 'bg-gray-300'"
          />
          <span class="truncate">{{ pipeline.name }}</span>
          <span class="ml-auto text-xs text-gray-400">
            {{ pipeline.channels?.length || 0 }} Kanaele
          </span>
        </button>
        <div
          v-if="engagementStore.activePipelines.length === 0"
          class="px-4 py-3 text-center text-sm text-gray-400"
        >
          Keine Pipelines vorhanden
        </div>
      </div>

      <!-- Overlay to close -->
      <div
        v-if="pipelineMenuOpen"
        class="fixed inset-0 z-[-1]"
        @click="pipelineMenuOpen = false"
      />
    </div>

    <!-- Right: Action buttons -->
    <div class="flex items-center gap-1">
      <!-- AI Sparkle (Chat) -->
      <button
        class="rounded-lg p-2 text-gray-500 transition hover:bg-gray-100 hover:text-go4-secondary dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-gray-200"
        title="KI-Assistent"
        @click="layout.toggleChat"
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
            d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z"
          />
        </svg>
      </button>

      <!-- Dark/Light Toggle -->
      <button
        class="rounded-lg p-2 text-gray-500 transition hover:bg-gray-100 hover:text-go4-secondary dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-gray-200"
        :title="layout.darkMode ? 'Light Mode' : 'Dark Mode'"
        @click="layout.toggleDarkMode"
      >
        <!-- Sun (shown in dark mode) -->
        <svg
          v-if="layout.darkMode"
          class="h-5 w-5"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M12 3v2.25m6.364.386l-1.591 1.591M21 12h-2.25m-.386 6.364l-1.591-1.591M12 18.75V21m-4.773-4.227l-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z"
          />
        </svg>
        <!-- Moon (shown in light mode) -->
        <svg
          v-else
          class="h-5 w-5"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M21.752 15.002A9.718 9.718 0 0118 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 003 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 009.002-5.998z"
          />
        </svg>
      </button>

      <!-- User Menu -->
      <div class="relative">
        <button
          class="flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm text-gray-600 transition hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
          @click="userMenuOpen = !userMenuOpen"
        >
          <div
            class="flex h-7 w-7 items-center justify-center rounded-full bg-go4-primary/10 text-xs font-semibold text-go4-primary"
          >
            {{ authStore.user?.display_name?.charAt(0)?.toUpperCase() || 'U' }}
          </div>
          <span class="hidden sm:inline">{{ authStore.user?.display_name || 'User' }}</span>
          <svg
            class="h-4 w-4"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M19.5 8.25l-7.5 7.5-7.5-7.5"
            />
          </svg>
        </button>

        <!-- Dropdown -->
        <div
          v-if="userMenuOpen"
          class="absolute right-0 top-full mt-1 w-56 rounded-lg border border-gray-200 bg-white py-1 shadow-lg dark:border-gray-700 dark:bg-gray-800"
        >
          <div class="border-b border-gray-100 px-4 py-2.5 dark:border-gray-700">
            <p class="text-sm font-medium text-gray-900 dark:text-gray-100">
              {{ authStore.user?.display_name }}
            </p>
            <p class="text-xs text-gray-500 dark:text-gray-400">
              {{ authStore.user?.email }}
            </p>
          </div>
          <button
            class="flex w-full items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700"
            @click="openPasswordModal"
          >
            <svg
              class="h-4 w-4"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z"
              />
            </svg>
            Passwort aendern
          </button>
          <button
            class="flex w-full items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
            @click="handleLogout"
          >
            <svg
              class="h-4 w-4"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15m3 0l3-3m0 0l-3-3m3 3H9"
              />
            </svg>
            Abmelden
          </button>
        </div>

        <!-- Overlay to close menu -->
        <div
          v-if="userMenuOpen"
          class="fixed inset-0 z-[-1]"
          @click="closeMenuOnOutsideClick"
        />
      </div>
    </div>
  </header>

  <!-- Password Change Modal -->
  <PasswordChangeModal
    v-if="showPasswordModal"
    @close="showPasswordModal = false"
  />
</template>
