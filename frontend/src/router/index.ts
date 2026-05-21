import { createRouter, createWebHistory } from 'vue-router'
import api from '@/api'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/dashboard',
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/Login.vue'),
      meta: { public: true },
    },
    {
      path: '/dashboard',
      name: 'Dashboard',
      component: () => import('@/views/Dashboard.vue'),
    },
    {
      path: '/reports',
      name: 'Reports',
      component: () => import('@/views/Reports.vue'),
    },
    {
      path: '/accounts',
      name: 'Accounts',
      component: () => import('@/views/Accounts.vue'),
    },
    {
      path: '/holdings',
      name: 'Holdings',
      component: () => import('@/views/Holdings.vue'),
    },
    {
      path: '/liabilities',
      name: 'Liabilities',
      component: () => import('@/views/Liabilities.vue'),
    },
    {
      path: '/expenses',
      name: 'Expenses',
      component: () => import('@/views/Expenses.vue'),
    },
    {
      path: '/settings',
      name: 'Settings',
      component: () => import('@/views/Settings.vue'),
    },
  ],
})

// Auth guard
let authChecked = false

router.beforeEach(async (to, _from, next) => {
  if (to.meta.public) return next()

  // Check auth status once per session
  if (!authChecked) {
    try {
      const { data } = await api.get('/auth/status')
      if (!data.enabled) {
        authChecked = true
        return next()
      }
      // Auth enabled — check token
      const token = localStorage.getItem('auth_token')
      if (token) {
        try {
          await api.post('/auth/verify', `token=${token}`)
          authChecked = true
          return next()
        } catch {}
      }
      return next('/login')
    } catch {
      return next()
    }
  }

  // Already checked: if auth enabled and no token, redirect
  const token = localStorage.getItem('auth_token')
  if (!token) {
    try {
      const { data } = await api.get('/auth/status')
      if (data.enabled) return next('/login')
    } catch {}
  }
  next()
})

export default router
