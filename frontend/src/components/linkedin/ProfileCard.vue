<script setup>
/**
 * Wiederverwendbare LinkedIn-Profil-Darstellung.
 * Wird im Debug-Tab (scrapeResult.profile) und in der Kontakt-Detailansicht verwendet.
 *
 * Props:
 *   profile  — das Profil-Objekt (aus Scraper oder DB/raw_data merge)
 *   showJson — ob JSON-Collapse angezeigt wird (default: true)
 */
defineProps({
  profile: { type: Object, default: () => ({}) },
  showJson: { type: Boolean, default: true }
})
</script>

<template>
  <div v-if="profile" class="space-y-4">
    <!-- Profile Summary Card -->
    <div class="rounded-lg border border-green-300 bg-green-50 p-4 dark:border-green-700 dark:bg-green-900/20">
      <div class="flex items-start gap-4">
        <img v-if="profile.profile_picture_url" :src="profile.profile_picture_url" class="h-16 w-16 rounded-full object-cover" />
        <div class="flex-1">
          <a
            v-if="profile.linkedin_url"
            :href="profile.linkedin_url"
            target="_blank"
            class="text-lg font-bold text-gray-900 hover:text-[#0A66C2] hover:underline dark:text-white dark:hover:text-[#0A66C2]"
          >{{ profile.name || 'Unbekannt' }}</a>
          <p v-else class="text-lg font-bold text-gray-900 dark:text-white">{{ profile.name || 'Unbekannt' }}</p>
          <p class="text-sm text-gray-700 dark:text-gray-300">{{ profile.headline || '' }}</p>
          <div class="mt-1 flex flex-wrap gap-3 text-xs text-gray-600 dark:text-gray-400">
            <span v-if="profile.location">{{ profile.location }}</span>
            <span v-if="profile.company_name">{{ profile.company_name }}</span>
            <span v-if="profile.follower_count">{{ profile.follower_count }} Follower</span>
            <span v-if="profile.connection_count">{{ profile.connection_count }}+ Kontakte</span>
            <span v-if="profile.is_premium" class="text-amber-600">Premium</span>
            <span v-if="profile.connection_status" class="font-medium text-blue-600">{{ profile.connection_status }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- About -->
    <div v-if="profile.summary" class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
      <h4 class="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">Info</h4>
      <p class="whitespace-pre-line text-sm text-gray-600 dark:text-gray-400">{{ profile.summary }}</p>
    </div>

    <!-- Experience -->
    <div v-if="profile.experience?.length" class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
      <h4 class="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">Berufserfahrung ({{ profile.experience.length }})</h4>
      <div v-for="(exp, i) in profile.experience" :key="i" class="mb-3 border-b border-gray-100 pb-3 last:mb-0 last:border-0 last:pb-0 dark:border-gray-700">
        <p class="font-medium text-gray-900 dark:text-white">{{ exp.title }}</p>
        <p class="text-sm text-gray-600 dark:text-gray-400">
          <a v-if="exp.company_linkedin_url" :href="exp.company_linkedin_url" target="_blank" class="hover:text-[#0A66C2] hover:underline">{{ exp.company }}</a>
          <span v-else>{{ exp.company }}</span>
          <span v-if="exp.employment_type" class="text-gray-400"> · {{ exp.employment_type }}</span>
        </p>
        <p v-if="exp.date_range" class="text-xs text-gray-500">{{ exp.date_range }} <span v-if="exp.duration" class="text-gray-400">· {{ exp.duration }}</span></p>
        <p v-if="exp.location" class="text-xs text-gray-500">{{ exp.location }}</p>
        <p v-if="exp.description" class="mt-1 text-xs text-gray-500 dark:text-gray-400">{{ exp.description.substring(0, 200) }}{{ exp.description.length > 200 ? '...' : '' }}</p>
      </div>
    </div>

    <!-- Education -->
    <div v-if="profile.education?.length" class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
      <h4 class="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">Ausbildung ({{ profile.education.length }})</h4>
      <div v-for="(edu, i) in profile.education" :key="i" class="mb-2 last:mb-0">
        <p class="font-medium text-gray-900 dark:text-white">{{ edu.school }}</p>
        <p v-if="edu.degree" class="text-sm text-gray-600 dark:text-gray-400">{{ edu.degree }}</p>
        <p v-if="edu.start_year || edu.end_year" class="text-xs text-gray-500">{{ edu.start_year || '' }} – {{ edu.end_year || '' }}</p>
        <p v-if="edu.description" class="mt-1 text-xs text-gray-500 dark:text-gray-400">{{ edu.description }}</p>
      </div>
    </div>

    <!-- Skills -->
    <div v-if="profile.skills?.length" class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
      <h4 class="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">Skills ({{ profile.skills.length }})</h4>
      <div class="flex flex-wrap gap-2">
        <span v-for="skill in profile.skills" :key="typeof skill === 'string' ? skill : skill.name" class="rounded-full bg-blue-100 px-3 py-1 text-xs text-blue-800 dark:bg-blue-900/30 dark:text-blue-300">{{ typeof skill === 'string' ? skill : skill.name }}</span>
      </div>
    </div>

    <!-- Languages + Certifications + Contact Info row -->
    <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
      <div v-if="profile.languages?.length" class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
        <h4 class="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">Sprachen</h4>
        <div v-for="lang in profile.languages" :key="lang.language || lang.name" class="text-sm text-gray-600 dark:text-gray-400">
          {{ lang.language || lang.name }} <span v-if="lang.proficiency" class="text-xs text-gray-400">· {{ lang.proficiency }}</span>
        </div>
      </div>
      <div v-if="profile.certifications?.length" class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
        <h4 class="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">Zertifikate</h4>
        <div v-for="cert in profile.certifications" :key="cert.name" class="mb-1 text-sm text-gray-600 dark:text-gray-400">
          <span class="font-medium">{{ cert.name }}</span>
          <span v-if="cert.issuer" class="text-xs text-gray-400"> · {{ cert.issuer }}</span>
        </div>
      </div>
      <div v-if="profile.contact_info" class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
        <h4 class="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">Kontaktdaten</h4>
        <div class="space-y-1 text-sm text-gray-600 dark:text-gray-400">
          <p v-if="profile.contact_info.email">Email: {{ profile.contact_info.email }}</p>
          <p v-if="profile.contact_info.phone">Telefon: {{ profile.contact_info.phone }}</p>
          <p v-if="profile.contact_info.website">Web: {{ profile.contact_info.website }}</p>
          <p v-if="profile.contact_info.address">Adresse: {{ profile.contact_info.address }}</p>
          <p v-if="profile.contact_info.birthday">Geburtstag: {{ profile.contact_info.birthday }}</p>
          <p v-if="profile.contact_info.twitter_url">Twitter: {{ profile.contact_info.twitter_url }}</p>
          <p v-if="profile.contact_info.connected_since">Vernetzt seit: {{ profile.contact_info.connected_since }}</p>
        </div>
      </div>
    </div>

    <!-- Interests -->
    <div v-if="profile.interests && Object.values(profile.interests).some(v => v?.length)" class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
      <h4 class="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">Interessen</h4>
      <div class="grid grid-cols-2 gap-3 md:grid-cols-5">
        <div v-for="(items, cat) in profile.interests" :key="cat">
          <p v-if="items?.length" class="mb-1 text-xs font-medium uppercase text-gray-500">{{ cat }}</p>
          <p v-for="item in items" :key="item" class="text-xs text-gray-600 dark:text-gray-400">{{ item }}</p>
        </div>
      </div>
    </div>

    <!-- Hashtags -->
    <div v-if="profile.hashtags?.length" class="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
      <h4 class="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">Hashtags</h4>
      <div class="flex flex-wrap gap-2">
        <span v-for="tag in profile.hashtags" :key="tag" class="rounded-full bg-gray-100 px-3 py-1 text-xs text-gray-700 dark:bg-gray-700 dark:text-gray-300">#{{ tag }}</span>
      </div>
    </div>

    <!-- Collapsible: Full Profile JSON -->
    <details v-if="showJson" class="rounded-lg border border-gray-200 dark:border-gray-700">
      <summary class="cursor-pointer rounded-t-lg bg-gray-50 px-4 py-3 text-sm font-medium text-gray-700 dark:bg-gray-800 dark:text-gray-300">
        Komplettes Profil JSON ({{ Object.keys(profile).length }} Felder)
      </summary>
      <pre class="max-h-96 overflow-auto p-4 font-mono text-xs text-gray-800 dark:text-gray-200">{{ JSON.stringify(profile, null, 2) }}</pre>
    </details>
  </div>
</template>
