<script setup>
const props = defineProps({
  weather: { type: Object, default: null },
  loading: { type: Boolean, default: false }
})
</script>

<template>
  <div class="rounded-lg bg-white p-6 shadow-sm">
    <h3 class="text-sm font-medium text-go4-muted">
      Wetter-Boost
    </h3>
    <div
      v-if="props.loading"
      class="mt-4 flex items-center justify-center"
    >
      <span class="text-go4-muted">Laden...</span>
    </div>
    <div
      v-else-if="!props.weather"
      class="mt-4 text-sm text-go4-muted"
    >
      Wetterdaten nicht verfuegbar
    </div>
    <div
      v-else
      class="mt-4 space-y-3"
    >
      <div class="flex items-center justify-between">
        <span class="text-2xl font-semibold text-go4-secondary">
          {{ props.weather.temp.toFixed(1) }}&#176;C
        </span>
        <span
          :class="[
            'rounded-full px-3 py-1 text-xs font-medium',
            props.weather.is_sunny ? 'bg-yellow-100 text-yellow-800' : 'bg-gray-100 text-gray-600'
          ]"
        >
          {{ props.weather.is_sunny ? 'Boost aktiv' : 'Kein Boost' }}
        </span>
      </div>
      <p class="text-sm text-go4-muted">
        {{ props.weather.description }}
      </p>
      <div class="flex items-center gap-4 text-xs text-go4-muted">
        <span>Wolken: {{ props.weather.clouds_percent }}%</span>
      </div>
    </div>
  </div>
</template>
