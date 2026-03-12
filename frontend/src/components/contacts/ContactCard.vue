<script setup>
import AvatarInitials from '@/components/ui/AvatarInitials.vue'

const props = defineProps({
  contact: { type: Object, required: true }
})

const emit = defineEmits(['click', 'email', 'call'])

function onClick() {
  emit('click', props.contact)
}

function onEmail(e) {
  e.stopPropagation()
  emit('email', props.contact)
}

function onCall(e) {
  e.stopPropagation()
  emit('call', props.contact)
}
</script>

<template>
  <div
    class="group cursor-pointer rounded-lg bg-white dark:bg-gray-800 p-4 shadow-sm hover:shadow-md transition-shadow border border-gray-200 dark:border-gray-700"
    @click="onClick"
  >
    <div class="flex items-start gap-3">
      <AvatarInitials
        :name="contact.name"
        :image-url="contact.avatar_url"
        size="lg"
      />

      <div class="flex-1 min-w-0">
        <h3 class="font-medium text-gray-900 dark:text-gray-100 truncate">
          {{ contact.name }}
        </h3>
        <p
          v-if="contact.position"
          class="text-sm text-gray-500 dark:text-gray-400 truncate"
        >
          {{ contact.position }}
        </p>
        <p
          v-if="contact.company_name"
          class="text-sm text-go4-primary dark:text-go4-primary-light truncate"
        >
          {{ contact.company_name }}
        </p>
      </div>
    </div>

    <div class="mt-3 space-y-1">
      <div class="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
        <svg
          class="h-4 w-4 flex-shrink-0"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
          />
        </svg>
        <span class="truncate">{{ contact.email }}</span>
      </div>
      <div
        v-if="contact.phone"
        class="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400"
      >
        <svg
          class="h-4 w-4 flex-shrink-0"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"
          />
        </svg>
        <span class="truncate">{{ contact.phone }}</span>
      </div>
    </div>

    <!-- Tags -->
    <div
      v-if="contact.tags && contact.tags.length > 0"
      class="mt-3 flex flex-wrap gap-1"
    >
      <span
        v-for="tag in contact.tags.slice(0, 3)"
        :key="tag"
        class="inline-flex items-center rounded-full bg-gray-100 dark:bg-gray-700 px-2 py-0.5 text-xs text-gray-700 dark:text-gray-300"
      >
        {{ tag }}
      </span>
      <span
        v-if="contact.tags.length > 3"
        class="inline-flex items-center rounded-full bg-gray-100 dark:bg-gray-700 px-2 py-0.5 text-xs text-gray-500 dark:text-gray-400"
      >
        +{{ contact.tags.length - 3 }}
      </span>
    </div>

    <!-- Quick Actions -->
    <div
      class="mt-3 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity border-t border-gray-100 dark:border-gray-700 pt-3"
    >
      <button
        type="button"
        class="flex-1 flex items-center justify-center gap-1 rounded-lg bg-gray-100 dark:bg-gray-700 px-3 py-1.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
        @click="onEmail"
      >
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
            d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
          />
        </svg>
        E-Mail
      </button>
      <button
        v-if="contact.phone"
        type="button"
        class="flex-1 flex items-center justify-center gap-1 rounded-lg bg-gray-100 dark:bg-gray-700 px-3 py-1.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
        @click="onCall"
      >
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
            d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"
          />
        </svg>
        Anrufen
      </button>
    </div>
  </div>
</template>
