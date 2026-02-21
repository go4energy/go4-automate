<script setup>
import { onMounted } from 'vue'
import { useChannelsStore } from '@/stores/channels'
import ChannelCard from '@/components/ChannelCard.vue'

const channels = useChannelsStore()

onMounted(async () => {
  await channels.fetchChannels()
  await channels.fetchSubscriptions()
})
</script>

<template>
  <div class="px-4 pb-4 pt-6">
    <h1 class="mb-4 text-2xl font-bold text-gray-900">Channels</h1>

    <div v-if="channels.loading" class="py-12 text-center text-gray-500">Laden...</div>

    <div v-else-if="channels.error" class="rounded-lg bg-red-50 p-4 text-sm text-red-700">
      {{ channels.error }}
    </div>

    <div v-else-if="channels.channels.length === 0" class="py-12 text-center">
      <p class="text-sm text-gray-500">Keine Channels verfuegbar.</p>
    </div>

    <div v-else class="space-y-3">
      <ChannelCard
        v-for="channel in channels.channels"
        :key="channel.id"
        :channel="channel"
        :subscribed="channels.subscribedIds.includes(channel.id)"
        @subscribe="channels.subscribe(channel.id)"
        @unsubscribe="channels.unsubscribe(channel.id)"
        @click="$router.push({ name: 'channel-detail', params: { id: channel.id } })"
      />
    </div>
  </div>
</template>
