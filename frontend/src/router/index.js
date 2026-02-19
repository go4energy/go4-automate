import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'dashboard',
    component: () => import('@/views/DashboardView.vue')
  },
  {
    path: '/leads',
    name: 'leads',
    component: () => import('@/views/LeadsView.vue')
  },
  {
    path: '/content',
    name: 'content',
    component: () => import('@/views/ContentDashboardView.vue')
  },
  {
    path: '/content/:id',
    name: 'content-edit',
    component: () => import('@/views/ContentEditView.vue'),
    props: true
  },
  {
    path: '/ads',
    name: 'ads',
    component: () => import('@/views/AdDashboardView.vue')
  },
  {
    path: '/ads/campaigns/:id/config',
    name: 'ad-campaign-config',
    component: () => import('@/views/AdCampaignConfigView.vue'),
    props: true
  },
  {
    path: '/research',
    name: 'research',
    component: () => import('@/views/ResearchView.vue')
  },
  {
    path: '/research/sources/new',
    name: 'research-source-new',
    component: () => import('@/views/ResearchSourceEditView.vue')
  },
  {
    path: '/research/sources/:id',
    name: 'research-source-edit',
    component: () => import('@/views/ResearchSourceEditView.vue'),
    props: true
  },
  {
    path: '/research/topics/new',
    name: 'research-topic-new',
    component: () => import('@/views/TopicCreateView.vue')
  },
  {
    path: '/prompts',
    name: 'prompts',
    component: () => import('@/views/PromptsView.vue')
  },
  {
    path: '/prompts/new',
    name: 'prompt-new',
    component: () => import('@/views/PromptEditorView.vue')
  },
  {
    path: '/prompts/:id',
    name: 'prompt-edit',
    component: () => import('@/views/PromptEditorView.vue'),
    props: true
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
