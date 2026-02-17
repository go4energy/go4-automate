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
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
