<script setup>
import AvatarInitials from '@/components/ui/AvatarInitials.vue'

const props = defineProps({
  company: { type: Object, required: true }
})

const emit = defineEmits(['click'])

function onClick() {
  emit('click', props.company)
}

function getInitials(name) {
  return name
    .split(' ')
    .map((w) => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()
}
</script>

<template>
  <div
    class="group cursor-pointer rounded-lg bg-white dark:bg-gray-800 p-4 shadow-sm hover:shadow-md transition-shadow border border-gray-200 dark:border-gray-700"
    @click="onClick"
  >
    <div class="flex items-start gap-3">
      <div
        v-if="company.logo_url"
        class="h-12 w-12 flex-shrink-0 rounded-lg bg-gray-100 dark:bg-gray-700 p-1"
      >
        <img
          :src="company.logo_url"
          :alt="company.name"
          class="h-full w-full object-contain"
        >
      </div>
      <AvatarInitials
        v-else
        :name="company.name"
        size="lg"
        color="bg-indigo-500"
      />

      <div class="flex-1 min-w-0">
        <h3 class="font-medium text-gray-900 dark:text-gray-100 truncate">
          {{ company.name }}
        </h3>
        <p
          v-if="company.industry"
          class="text-sm text-gray-500 dark:text-gray-400 truncate"
        >
          {{ company.industry }}
        </p>
        <p
          v-if="company.website"
          class="text-sm text-go4-primary dark:text-go4-primary-light truncate"
        >
          {{ company.domain || company.website }}
        </p>
      </div>
    </div>

    <div class="mt-3 flex items-center justify-between text-sm">
      <div class="flex items-center gap-2 text-gray-600 dark:text-gray-400">
        <svg
          class="h-4 w-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"
          />
        </svg>
        <span>{{ company.contact_count || 0 }} Kontakte</span>
      </div>

      <span
        v-if="company.size"
        class="inline-flex items-center rounded-full bg-gray-100 dark:bg-gray-700 px-2 py-0.5 text-xs text-gray-600 dark:text-gray-400"
      >
        {{ company.size }}
      </span>
    </div>

    <!-- Tags -->
    <div
      v-if="company.tags && company.tags.length > 0"
      class="mt-3 flex flex-wrap gap-1"
    >
      <span
        v-for="tag in company.tags.slice(0, 3)"
        :key="tag"
        class="inline-flex items-center rounded-full bg-indigo-100 dark:bg-indigo-900/30 px-2 py-0.5 text-xs text-indigo-700 dark:text-indigo-300"
      >
        {{ tag }}
      </span>
      <span
        v-if="company.tags.length > 3"
        class="inline-flex items-center rounded-full bg-gray-100 dark:bg-gray-700 px-2 py-0.5 text-xs text-gray-500 dark:text-gray-400"
      >
        +{{ company.tags.length - 3 }}
      </span>
    </div>
  </div>
</template>
