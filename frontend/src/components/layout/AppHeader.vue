<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLayoutStore } from '@/stores/layout'
import { useAuthStore } from '@/stores/auth'
import { usePageTopics } from '@/stores/pageTopics'
import {
  usePipelineContext,
  OUTREACH_MODULE_CHANNELS,
} from '@/stores/pipelineContext'
import PasswordChangeModal from '@/components/auth/PasswordChangeModal.vue'

const route = useRoute()
const router = useRouter()
const layout = useLayoutStore()
const authStore = useAuthStore()
const pageTopics = usePageTopics()
const pipelineCtx = usePipelineContext()

const hasPageHelp = computed(() => pageTopics.topics.length > 0)
const helpButtonTitle = computed(() =>
  hasPageHelp.value
    ? `Hilfe verfügbar zu: ${pageTopics.topics.map((t) => t.title).join(', ')}`
    : 'KI-Assistent',
)

const userMenuOpen = ref(false)
const showPasswordModal = ref(false)
const pipelineMenuOpen = ref(false)

const showPipelineSelector = computed(() =>
  Object.prototype.hasOwnProperty.call(
    OUTREACH_MODULE_CHANNELS,
    pipelineCtx.currentModuleKey,
  ),
)

const sortedPipelines = computed(() =>
  [...pipelineCtx.pipelinesForCurrentModule].sort((a, b) =>
    (a.name || '').localeCompare(b.name || ''),
  ),
)

function selectPipeline(id) {
  pipelineCtx.setActivePipeline(id)
  pipelineMenuOpen.value = false
  // Mirror selection in URL so deep links / refresh keep state.
  const next = { ...route.query }
  if (id) next.pipeline = String(id)
  else delete next.pipeline
  router.replace({ path: route.path, query: next })
}

onMounted(() => {
  if (showPipelineSelector.value) pipelineCtx.ensurePipelines()
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


    <!-- Center: Pipeline Selector (Outreach modules only) -->
    <div
      v-if="showPipelineSelector"
      class="relative"
    >
      <button
        type="button"
        class="flex items-center gap-2 rounded-lg border border-gray-200 bg-white/70 px-3 py-1.5 text-sm text-gray-700 hover:border-go4-primary hover:text-go4-primary dark:border-gray-700 dark:bg-gray-800/70 dark:text-gray-200 dark:hover:border-go4-primary"
        @click="pipelineMenuOpen = !pipelineMenuOpen"
      >
        <svg
          class="h-4 w-4 text-gray-400"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M3.75 6.75h16.5M3.75 12h16.5M3.75 17.25h16.5"
          />
        </svg>
        <span
          class="max-w-[16rem] truncate"
          :class="!pipelineCtx.isActive ? 'text-gray-400 italic' : ''"
        >{{ pipelineCtx.label }}</span>
        <svg
          class="h-4 w-4 text-gray-400"
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

      <div
        v-if="pipelineMenuOpen"
        class="absolute left-0 top-full z-30 mt-1 w-80 rounded-lg border border-gray-200 bg-white py-1 shadow-lg dark:border-gray-700 dark:bg-gray-800"
      >
        <div
          v-if="sortedPipelines.length === 0"
          class="px-3 py-3 text-sm text-gray-500 dark:text-gray-400"
        >
          Es gibt noch keine Pipeline, die dieses Modul benutzt.<br>
          Bitte zuerst im Engagement-Modul anlegen.
          <router-link
            to="/engagement"
            class="mt-2 block text-go4-primary hover:text-go4-primary-dark"
            @click="pipelineMenuOpen = false"
          >
            Zum Engagement →
          </router-link>
        </div>
        <button
          v-for="p in sortedPipelines"
          :key="p.id"
          type="button"
          class="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-700"
          :class="
            p.id === pipelineCtx.activePipelineId
              ? 'bg-go4-primary/5 font-medium text-go4-primary'
              : 'text-gray-700 dark:text-gray-200'
          "
          @click="selectPipeline(p.id)"
        >
          <span class="truncate">{{ p.name }}</span>
          <span
            v-if="!p.is_active"
            class="ml-2 rounded bg-gray-100 px-1.5 py-0.5 text-[10px] uppercase text-gray-500 dark:bg-gray-700 dark:text-gray-400"
          >
            inaktiv
          </span>
        </button>
      </div>

      <!-- Backdrop -->
      <div
        v-if="pipelineMenuOpen"
        class="fixed inset-0 z-20"
        @click="pipelineMenuOpen = false"
      />
    </div>

    <!-- Right: Action buttons -->
    <div class="flex items-center gap-1">
      <!-- AI Sparkle (Chat) — turns green when the current page has help-topics -->
      <button
        class="relative rounded-lg p-2 transition"
        :class="
          hasPageHelp
            ? 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200 dark:bg-emerald-900/40 dark:text-emerald-300 dark:hover:bg-emerald-900/60'
            : 'text-gray-500 hover:bg-gray-100 hover:text-go4-secondary dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-gray-200'
        "
        :title="helpButtonTitle"
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
        <span
          v-if="hasPageHelp"
          class="absolute right-1 top-1 h-2 w-2 rounded-full bg-emerald-500 ring-2 ring-white dark:ring-gray-800"
        />
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
