import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    component: () => import('@/components/layout/AppLayout.vue'),
    children: [
      {
        path: '',
        name: 'dashboard',
        component: () => import('@/views/DashboardView.vue'),
        meta: { title: 'Dashboard' }
      },
      {
        path: 'leads',
        name: 'leads',
        component: () => import('@/views/LeadsView.vue'),
        meta: { title: 'Leads' }
      },
      {
        path: 'content',
        name: 'content',
        component: () => import('@/views/ContentDashboardView.vue'),
        meta: { title: 'Content' }
      },
      {
        path: 'content/:id',
        name: 'content-edit',
        component: () => import('@/views/ContentEditView.vue'),
        props: true,
        meta: { title: 'Bearbeiten', parent: 'content' }
      },
      {
        path: 'ads',
        name: 'ads',
        component: () => import('@/views/AdDashboardView.vue'),
        meta: { title: 'Ad Management' }
      },
      {
        path: 'ads/campaigns/:id/config',
        name: 'ad-campaign-config',
        component: () => import('@/views/AdCampaignConfigView.vue'),
        props: true,
        meta: { title: 'Kampagne konfigurieren', parent: 'ads' }
      },
      {
        path: 'research',
        name: 'research',
        component: () => import('@/views/ResearchView.vue'),
        meta: { title: 'Research Agent' }
      },
      {
        path: 'research/sources/new',
        name: 'research-source-new',
        component: () => import('@/views/ResearchSourceEditView.vue'),
        meta: { title: 'Neue Quelle', parent: 'research' }
      },
      {
        path: 'research/sources/:id',
        name: 'research-source-edit',
        component: () => import('@/views/ResearchSourceEditView.vue'),
        props: true,
        meta: { title: 'Quelle bearbeiten', parent: 'research' }
      },
      {
        path: 'research/topics/new',
        name: 'research-topic-new',
        component: () => import('@/views/TopicCreateView.vue'),
        meta: { title: 'Eigenes Thema', parent: 'research' }
      },
      {
        path: 'prompts',
        name: 'prompts',
        component: () => import('@/views/PromptsView.vue'),
        meta: { title: 'Prompt Registry' }
      },
      {
        path: 'prompts/new',
        name: 'prompt-new',
        component: () => import('@/views/PromptEditorView.vue'),
        meta: { title: 'Neuer Prompt', parent: 'prompts' }
      },
      {
        path: 'prompts/:id',
        name: 'prompt-edit',
        component: () => import('@/views/PromptEditorView.vue'),
        props: true,
        meta: { title: 'Prompt bearbeiten', parent: 'prompts' }
      },
      {
        path: 'setup',
        name: 'setup',
        component: () => import('@/views/SetupView.vue'),
        meta: { title: 'Setup Wizard' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
