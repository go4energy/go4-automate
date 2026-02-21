<script setup>
defineProps({
  channel: { type: Object, required: true },
  subscribed: { type: Boolean, default: false }
})

const emit = defineEmits(['subscribe', 'unsubscribe'])
</script>

<template>
  <div class="cursor-pointer rounded-xl bg-white p-4 shadow-sm transition-shadow hover:shadow-md">
    <div class="flex items-start justify-between gap-3">
      <div class="min-w-0 flex-1">
        <h3 class="text-sm font-semibold text-gray-900">{{ channel.name }}</h3>
        <p v-if="channel.description" class="mt-0.5 line-clamp-2 text-xs text-gray-500">
          {{ channel.description }}
        </p>
        <div v-if="channel.categories?.length" class="mt-2 flex flex-wrap gap-1">
          <span
            v-for="cat in channel.categories.slice(0, 3)"
            :key="cat"
            class="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600"
          >
            {{ cat }}
          </span>
        </div>
        <p v-if="channel.schedule" class="mt-2 text-xs text-gray-400">
          {{ channel.schedule }}
        </p>
      </div>
      <button
        class="shrink-0 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors"
        :class="
          subscribed
            ? 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            : 'bg-go4-primary text-white hover:bg-go4-primary-dark'
        "
        @click.stop="subscribed ? emit('unsubscribe') : emit('subscribe')"
      >
        {{ subscribed ? 'Abonniert' : 'Abonnieren' }}
      </button>
    </div>
  </div>
</template>
