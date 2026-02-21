import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { guest: true }
    },
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeView.vue'),
      meta: { auth: true }
    },
    {
      path: '/channels',
      name: 'channels',
      component: () => import('@/views/ChannelListView.vue'),
      meta: { auth: true }
    },
    {
      path: '/channels/:id',
      name: 'channel-detail',
      component: () => import('@/views/ChannelDetailView.vue'),
      meta: { auth: true },
      props: true
    },
    {
      path: '/player',
      name: 'player',
      component: () => import('@/views/PlayerView.vue'),
      meta: { auth: true }
    },
    {
      path: '/profile',
      name: 'profile',
      component: () => import('@/views/ProfileView.vue'),
      meta: { auth: true }
    }
  ]
})

// Navigation Guard
router.beforeEach((to) => {
  const token = localStorage.getItem('listener_token')
  if (to.meta.auth && !token) {
    return { name: 'login' }
  }
  if (to.meta.guest && token) {
    return { name: 'home' }
  }
})

export default router
