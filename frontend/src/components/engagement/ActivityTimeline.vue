<script setup>
import { ref, onMounted, computed } from 'vue'
import { getContactActivities } from '@/api/engagement'

const props = defineProps({
  contactId: {
    type: Number,
    required: true
  },
  limit: {
    type: Number,
    default: 20
  }
})

const activities = ref([])
const loading = ref(false)
const error = ref(null)

// Channel icons
const channelIcons = {
  linkedin: {
    icon: 'M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z',
    color: 'text-blue-600 bg-blue-100'
  },
  email: {
    icon: 'M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z',
    color: 'text-green-600 bg-green-100'
  },
  phone: {
    icon: 'M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z',
    color: 'text-purple-600 bg-purple-100'
  },
  whatsapp: {
    icon: 'M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z',
    color: 'text-green-500 bg-green-100'
  },
  website: {
    icon: 'M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9',
    color: 'text-indigo-600 bg-indigo-100'
  },
  crm: {
    icon: 'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z',
    color: 'text-orange-600 bg-orange-100'
  },
  meeting: {
    icon: 'M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z',
    color: 'text-pink-600 bg-pink-100'
  }
}

// Direction icons
const directionClasses = computed(() => {
  return {
    outbound: 'border-r-4 border-blue-500',
    inbound: 'border-r-4 border-green-500'
  }
})

function getChannelConfig(channel) {
  return channelIcons[channel] || {
    icon: 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
    color: 'text-gray-600 bg-gray-100'
  }
}

function formatDate(dateString) {
  const date = new Date(dateString)
  const now = new Date()
  const diff = now - date
  const hours = Math.floor(diff / (1000 * 60 * 60))

  if (hours < 1) {
    const minutes = Math.floor(diff / (1000 * 60))
    return minutes <= 1 ? 'gerade eben' : `vor ${minutes} Min.`
  }
  if (hours < 24) {
    return `vor ${hours} Std.`
  }
  if (hours < 48) {
    return 'gestern'
  }

  return date.toLocaleDateString('de-DE', {
    day: 'numeric',
    month: 'short',
    year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
  })
}

function formatActivityType(type) {
  const typeLabels = {
    // LinkedIn
    connection_request_sent: 'Verbindungsanfrage gesendet',
    connection_request_accepted: 'Verbindung akzeptiert',
    message_sent: 'Nachricht gesendet',
    message_received: 'Nachricht erhalten',
    inmail_sent: 'InMail gesendet',
    profile_viewed: 'Profil angesehen',
    // Email
    email_sent: 'E-Mail gesendet',
    email_opened: 'E-Mail geöffnet',
    email_clicked: 'Link geklickt',
    email_replied: 'E-Mail beantwortet',
    email_bounced: 'E-Mail nicht zugestellt',
    email_unsubscribed: 'Abgemeldet',
    // Phone/CRM
    call_made: 'Anruf getätigt',
    call_received: 'Anruf erhalten',
    note_added: 'Notiz hinzugefügt',
    meeting_scheduled: 'Meeting geplant',
    meeting_completed: 'Meeting abgeschlossen',
    task_created: 'Aufgabe erstellt',
    task_completed: 'Aufgabe erledigt',
    deal_created: 'Deal erstellt',
    deal_stage_changed: 'Deal-Phase geändert',
    deal_won: 'Deal gewonnen',
    deal_lost: 'Deal verloren',
    // WhatsApp
    whatsapp_message_sent: 'WhatsApp gesendet',
    whatsapp_message_received: 'WhatsApp erhalten',
    // Website
    page_view: 'Seite besucht',
    form_submit: 'Formular abgesendet',
    cta_click: 'CTA geklickt'
  }
  return typeLabels[type] || type.replace(/_/g, ' ')
}

async function fetchActivities() {
  loading.value = true
  error.value = null
  try {
    const { data } = await getContactActivities(props.contactId, props.limit)
    activities.value = data
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    loading.value = false
  }
}

onMounted(fetchActivities)
</script>

<template>
  <div class="rounded-lg bg-white dark:bg-gray-800 p-6 shadow-sm">
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
        Aktivitäten
      </h2>
      <button
        v-if="activities.length > 0"
        type="button"
        class="text-sm text-go4-primary hover:underline"
        @click="fetchActivities"
      >
        Aktualisieren
      </button>
    </div>

    <!-- Loading -->
    <div
      v-if="loading"
      class="flex items-center justify-center py-8"
    >
      <span class="text-go4-muted dark:text-gray-400 text-sm">Laden...</span>
    </div>

    <!-- Error -->
    <div
      v-else-if="error"
      class="rounded-lg bg-red-50 dark:bg-red-900/20 p-4 text-red-700 dark:text-red-400 text-sm"
    >
      {{ error }}
    </div>

    <!-- Empty state -->
    <div
      v-else-if="activities.length === 0"
      class="text-center py-8 text-sm text-gray-500 dark:text-gray-400"
    >
      <svg
        class="mx-auto h-12 w-12 text-gray-300 dark:text-gray-600 mb-3"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="1"
          d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
      Noch keine Aktivitäten vorhanden.
    </div>

    <!-- Timeline -->
    <div
      v-else
      class="flow-root"
    >
      <ul class="-mb-8">
        <li
          v-for="(activity, index) in activities"
          :key="activity.id"
        >
          <div class="relative pb-8">
            <!-- Line connecting activities -->
            <span
              v-if="index !== activities.length - 1"
              class="absolute left-4 top-4 -ml-px h-full w-0.5 bg-gray-200 dark:bg-gray-700"
            />

            <div class="relative flex space-x-3">
              <!-- Icon -->
              <div>
                <span
                  :class="[
                    getChannelConfig(activity.channel).color,
                    'h-8 w-8 rounded-full flex items-center justify-center ring-4 ring-white dark:ring-gray-800'
                  ]"
                >
                  <svg
                    class="h-4 w-4"
                    fill="none"
                    :stroke="activity.channel === 'linkedin' || activity.channel === 'whatsapp' ? 'none' : 'currentColor'"
                    :fill-rule="activity.channel === 'linkedin' || activity.channel === 'whatsapp' ? 'evenodd' : undefined"
                    viewBox="0 0 24 24"
                  >
                    <path
                      v-if="activity.channel === 'linkedin' || activity.channel === 'whatsapp'"
                      fill="currentColor"
                      :d="getChannelConfig(activity.channel).icon"
                    />
                    <path
                      v-else
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      :d="getChannelConfig(activity.channel).icon"
                    />
                  </svg>
                </span>
              </div>

              <!-- Content -->
              <div
                class="flex min-w-0 flex-1 justify-between space-x-4 pt-1.5"
                :class="activity.direction ? directionClasses[activity.direction] : ''"
              >
                <div class="min-w-0 flex-1 pr-2">
                  <p class="text-sm text-gray-900 dark:text-gray-100 font-medium">
                    {{ formatActivityType(activity.activity_type) }}
                  </p>
                  <p
                    v-if="activity.subject"
                    class="text-sm text-gray-500 dark:text-gray-400 truncate"
                  >
                    {{ activity.subject }}
                  </p>
                </div>
                <div class="whitespace-nowrap text-right text-xs text-gray-500 dark:text-gray-400">
                  {{ formatDate(activity.performed_at) }}
                </div>
              </div>
            </div>
          </div>
        </li>
      </ul>
    </div>
  </div>
</template>
