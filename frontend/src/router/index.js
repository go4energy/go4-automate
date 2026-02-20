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
        path: 'collector',
        name: 'collector',
        component: () => import('@/views/CollectorView.vue'),
        meta: { title: 'Collector' }
      },
      {
        path: 'collector/sources/new',
        name: 'collector-source-new',
        component: () => import('@/views/CollectorSourceEditView.vue'),
        meta: { title: 'Neue Quelle', parent: 'collector' }
      },
      {
        path: 'collector/sources/:id',
        name: 'collector-source-edit',
        component: () => import('@/views/CollectorSourceEditView.vue'),
        props: true,
        meta: { title: 'Quelle bearbeiten', parent: 'collector' }
      },
      {
        path: 'collector/topics/new',
        name: 'collector-topic-new',
        component: () => import('@/views/CollectorTopicCreateView.vue'),
        meta: { title: 'Eigenes Thema', parent: 'collector' }
      },
      {
        path: 'creator',
        name: 'creator',
        component: () => import('@/views/CreatorDashboardView.vue'),
        meta: { title: 'Creator' }
      },
      {
        path: 'creator/:id',
        name: 'creator-edit',
        component: () => import('@/views/CreatorEditView.vue'),
        props: true,
        meta: { title: 'Bearbeiten', parent: 'creator' }
      },
      {
        path: 'distributor',
        name: 'distributor',
        component: () => import('@/views/DistributorDashboardView.vue'),
        meta: { title: 'Distributor' }
      },
      {
        path: 'distributor/campaigns/:id/config',
        name: 'distributor-campaign-config',
        component: () => import('@/views/DistributorCampaignConfigView.vue'),
        props: true,
        meta: { title: 'Kampagne konfigurieren', parent: 'distributor' }
      },
      {
        path: 'crm',
        name: 'crm',
        component: () => import('@/views/CrmView.vue'),
        meta: { title: 'CRM' }
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
