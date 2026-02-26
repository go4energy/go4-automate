<script setup>
import AvatarInitials from '@/components/ui/AvatarInitials.vue'

defineProps({
  prospect: { type: Object, required: true },
  compact: { type: Boolean, default: false }
})

defineEmits(['click', 'move', 'handoff'])

function getStatusColor(status) {
  switch (status) {
    case 'new':
      return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
    case 'contacted':
      return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
    case 'engaged':
      return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200'
    case 'qualified':
      return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
    case 'handed_off':
      return 'bg-teal-100 text-teal-800 dark:bg-teal-900 dark:text-teal-200'
    case 'do_not_contact':
      return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
    default:
      return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
  }
}

function getStatusLabel(status) {
  switch (status) {
    case 'new':
      return 'Neu'
    case 'contacted':
      return 'Kontaktiert'
    case 'engaged':
      return 'Interessiert'
    case 'qualified':
      return 'Qualifiziert'
    case 'handed_off':
      return 'Uebergeben'
    case 'do_not_contact':
      return 'Nicht kontaktieren'
    default:
      return status
  }
}
</script>

<template>
  <div
    class="group cursor-pointer rounded-lg bg-white dark:bg-gray-800 p-4 shadow-sm ring-1 ring-gray-200 dark:ring-gray-700 transition-all hover:shadow-md hover:ring-go4-primary"
    :class="{ 'p-3': compact }"
    @click="$emit('click', prospect)"
  >
    <div class="flex items-start gap-3">
      <!-- Avatar -->
      <AvatarInitials
        :name="prospect.name"
        :size="compact ? 'sm' : 'md'"
      />

      <!-- Content -->
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2">
          <h4
            class="font-medium text-go4-secondary dark:text-white truncate"
            :class="{ 'text-sm': compact }"
          >
            {{ prospect.name }}
          </h4>

          <!-- Duplicate warning -->
          <span
            v-if="prospect.is_duplicate"
            class="flex-shrink-0 rounded-full bg-yellow-100 p-0.5 text-yellow-600"
            title="Mögliches Duplikat"
          >
            <svg
              class="h-3 w-3"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fill-rule="evenodd"
                d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                clip-rule="evenodd"
              />
            </svg>
          </span>
        </div>

        <!-- Position / Company -->
        <p
          v-if="prospect.position || prospect.company_name"
          class="text-xs text-go4-muted dark:text-gray-400 truncate"
        >
          {{ prospect.position }}{{ prospect.position && prospect.company_name ? ' @ ' : ''
          }}{{ prospect.company_name }}
        </p>

        <!-- Email -->
        <p
          v-if="prospect.email && !compact"
          class="mt-1 text-xs text-go4-muted dark:text-gray-400 truncate"
        >
          {{ prospect.email }}
        </p>

        <!-- Footer: Score + Status -->
        <div
          v-if="!compact"
          class="mt-2 flex items-center justify-between"
        >
          <!-- Score -->
          <div class="flex items-center gap-1">
            <span class="text-xs text-go4-muted dark:text-gray-400">Score:</span>
            <span
              class="text-sm font-semibold"
              :class="{
                'text-green-600': prospect.score >= 70,
                'text-yellow-600': prospect.score >= 40 && prospect.score < 70,
                'text-gray-600 dark:text-gray-400': prospect.score < 40
              }"
            >
              {{ prospect.score }}
            </span>
          </div>

          <!-- Status -->
          <span
            class="rounded-full px-2 py-0.5 text-xs font-medium"
            :class="getStatusColor(prospect.status)"
          >
            {{ getStatusLabel(prospect.status) }}
          </span>
        </div>

        <!-- Tags (if not compact) -->
        <div
          v-if="!compact && prospect.tags?.length"
          class="mt-2 flex flex-wrap gap-1"
        >
          <span
            v-for="tag in prospect.tags.slice(0, 2)"
            :key="tag"
            class="inline-flex items-center rounded-full bg-gray-100 dark:bg-gray-700 px-2 py-0.5 text-xs text-gray-600 dark:text-gray-300"
          >
            {{ tag }}
          </span>
        </div>
      </div>

      <!-- LinkedIn Icon -->
      <a
        v-if="prospect.linkedin_url"
        :href="prospect.linkedin_url"
        target="_blank"
        class="flex-shrink-0 text-blue-500 hover:text-blue-700"
        title="LinkedIn"
        @click.stop
      >
        <svg
          class="h-4 w-4"
          fill="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"
          />
        </svg>
      </a>
    </div>
  </div>
</template>
