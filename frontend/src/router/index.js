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
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
